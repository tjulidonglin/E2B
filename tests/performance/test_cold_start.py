"""
E2B Sandbox Cold Start Test
"""

import os
import sys
import time
import statistics
from typing import List, Tuple, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from e2b_code_interpreter import Sandbox
except ImportError:
    print("Error: e2b_code_interpreter package not installed")
    sys.exit(1)

from tests.utils.metrics_collector import MetricsCollector
from tests.utils.report_generator import ReportGenerator


class ColdStartTest:
    """Cold start test class"""
    
    PROBE_CMD = "echo 1"
    PROBE_RETRY_INTERVAL = 0.02
    PROBE_TIMEOUT = 30
    
    def __init__(self, template: str = "base", report: ReportGenerator = None):
        self.template = template
        self.report = report or ReportGenerator()
        # 华为云配置：从环境变量读取
        self.api_url = os.environ.get("E2B_API_URL")
        self.sandbox_url = os.environ.get("E2B_SANDBOX_URL")
        self.api_key = os.environ.get("E2B_API_KEY")
    
    def _create_sandbox(self, timeout: int = 120):
        """创建 Sandbox 实例，自动注入华为云配置"""
        kwargs = {
            "template": self.template,
            "timeout": timeout,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_url:
            kwargs["api_url"] = self.api_url
        if self.sandbox_url:
            kwargs["sandbox_url"] = self.sandbox_url
        
        sbx = Sandbox.create(**kwargs)
        
        # 按需应用华为云补丁（标准 E2B 环境自动跳过）
        from utils.huawei_patch import patch_sandbox_if_needed
        patch_sandbox_if_needed(sbx)
        
        return sbx
    
    def _probe_sandbox_ready(self, sbx) -> Tuple[bool, float]:
        probe_start = time.perf_counter()
        while True:
            try:
                result = sbx.commands.run(self.PROBE_CMD, timeout=5)
                if result.exit_code == 0:
                    return True, time.perf_counter() - probe_start
            except Exception:
                pass
            if time.perf_counter() - probe_start > self.PROBE_TIMEOUT:
                return False, time.perf_counter() - probe_start
            time.sleep(self.PROBE_RETRY_INTERVAL)

    def _measure_rtt_baseline(self, sbx, probe_count: int = 30) -> float:
        """
        测量网络 RTT 基线（通过执行无实际工作的 echo 命令）。
        返回最小端到端时间（秒），近似等于纯网络 RTT（因为 echo 执行时间 ≈ 0）。
        """
        rtt_samples = []
        for _ in range(probe_count):
            start = time.perf_counter()
            try:
                sbx.commands.run("echo 1", timeout=5)
                elapsed = time.perf_counter() - start
                rtt_samples.append(elapsed)
            except Exception:
                pass
        return min(rtt_samples) if rtt_samples else 0.0
    
    def _measure_single_cold_start(self) -> Tuple[float, float, float, float, float]:
        """
        测量单次冷启动耗时。
        
        Returns:
            (e2e_create_time, probe_time, total_time, rtt_baseline, cloud_internal_time)
            cloud_internal_time = total_time - rtt_baseline (近似云平台内部耗时)
        """
        start = time.perf_counter()
        try:
            sbx = self._create_sandbox(timeout=120)
        except Exception as e:
            print(f"    Sandbox creation failed: {e}")
            return -1.0, -1.0, -1.0, 0.0, 0.0
        
        create_elapsed = time.perf_counter() - start
        ok, probe_elapsed = self._probe_sandbox_ready(sbx)
        total_elapsed = create_elapsed + probe_elapsed
        
        # 测量 RTT 基线（沙箱已就绪，执行 echo 最小耗时 ≈ 纯网络 RTT）
        rtt_baseline = self._measure_rtt_baseline(sbx, probe_count=30)
        
        # 估算：云平台内部耗时 = 总耗时 − 网络 RTT 基线
        cloud_internal_time = max(0.0, total_elapsed - rtt_baseline)
        
        if not ok:
            from utils.huawei_patch import safe_kill_sandbox
            safe_kill_sandbox(sbx)
            return create_elapsed, -1.0, -1.0, rtt_baseline, 0.0
        
        from utils.huawei_patch import safe_kill_sandbox
        safe_kill_sandbox(sbx)
        
        return create_elapsed, probe_elapsed, total_elapsed, rtt_baseline, cloud_internal_time
    
    def _run_single_test(self, test_num: int, total: int) -> Tuple[float, float, float]:
        return self._measure_single_cold_start()
    
    def run_sequential_test(self, runs: int = 10) -> Dict[str, Any]:
        print(f"\n{'='*60}")
        print(f"  Cold Start Time Test (Sequential)")
        print(f"  Runs: {runs}, Template: {self.template}")
        print(f"{'='*60}\n")
        
        results = []
        for i in range(runs):
            print(f"  [{i+1}/{runs}] Creating sandbox...", end="", flush=True)
            create_t, probe_t, total_t = self._measure_single_cold_start()
            if total_t < 0:
                print(f" FAILED")
                continue
            results.append((create_t, probe_t, total_t))
            print(f" OK | total={total_t:.3f}s")
            if i < runs - 1:
                time.sleep(0.5)
        return self._calculate_statistics(results, "Sequential")
    
    def run_concurrent_test(self, count: int = 10, concurrency: int = 5) -> Dict[str, Any]:
        print(f"\n{'='*60}")
        print(f"  Cold Start Time Test (Concurrent)")
        print(f"  Total: {count}, Concurrency: {concurrency}")
        print(f"{'='*60}\n")
        
        results = []
        failed = 0
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {
                executor.submit(self._run_single_test, i, count): i
                for i in range(1, count + 1)
            }
            for future in as_completed(futures):
                test_num = futures[future]
                try:
                    create_t, probe_t, total_t = future.result()
                    if total_t > 0:
                        results.append((create_t, probe_t, total_t))
                        print(f"  [{test_num}/{count}] OK | total={total_t:.3f}s")
                    else:
                        failed += 1
                        print(f"  [{test_num}/{count}] FAILED")
                except Exception as e:
                    failed += 1
        return self._calculate_statistics(results, "Concurrent", failed)
    
    def _calculate_statistics(self, results: List[Tuple], mode: str, failed: int = 0) -> Dict[str, Any]:
        if not results:
            print(f"\n  No valid results.")
            return {'success': False, 'error': 'No valid results'}
        
        create_times = [r[0] for r in results]
        probe_times = [r[1] for r in results]
        total_times = [r[2] for r in results]
        rtt_bases = [r[3] for r in results]
        cloud_times = [r[4] for r in results]
        
        def calc_stats(times: List[float]) -> Dict:
            if not times: return {}
            sorted_times = sorted(times)
            n = len(times)
            
            def percentile(p: float) -> float:
                """计算第 p 百分位数（p 为 0~1 之间的浮点数，如 0.95、0.99）"""
                if n == 1:
                    return times[0]
                idx = min(int(n * p), n - 1)
                return sorted_times[idx]
            
            return {
                'min': min(times), 'max': max(times),
                'mean': statistics.mean(times),
                'median': statistics.median(times) if n >= 2 else times[0],
                'p95': percentile(0.95),
                'p99': percentile(0.99),
            }
        
        create_stats = calc_stats(create_times)
        probe_stats = calc_stats(probe_times)
        total_stats = calc_stats(total_times)
        rtt_stats = calc_stats(rtt_bases)
        cloud_stats = calc_stats(cloud_times)
        
        print(f"\n{'='*60}")
        print(f"  Statistics ({mode})")
        print(f"{'='*60}")
        print(f"  Valid: {len(results)}, Failed: {failed}")
        print(f"\n  {'Metric':<12} {'Min':>10} {'Max':>10} {'Mean':>10} {'P95':>10} {'P99':>10}")
        for label, stats in [("Create", create_stats), ("Probe", probe_stats), ("Total", total_stats)]:
            if stats:
                print(f"  {label:<12} {stats['min']:>10.3f} {stats['max']:>10.3f} {stats['mean']:>10.3f} {stats['p95']:>10.3f} {stats['p99']:>10.3f}")
        
        # 输出 RTT 基线统计
        if rtt_stats:
            print(f"\n  --- Network RTT Baseline (网络 RTT 基线) ---")
            print(f"  {'Metric':<12} {'Min':>10} {'Max':>10} {'Mean':>10} {'P95':>10} {'P99':>10}")
            print(f"  {'RTT':<12} {rtt_stats['min']:>10.3f} {rtt_stats['max']:>10.3f} {rtt_stats['mean']:>10.3f} {rtt_stats['p95']:>10.3f} {rtt_stats['p99']:>10.3f}")
        
        # 输出云平台内部耗时统计（减去网络 RTT 基线后）
        if cloud_stats:
            print(f"\n  --- Cloud Platform Internal Time (云平台内部耗时) ---")
            print(f"  {'Metric':<12} {'Min':>10} {'Max':>10} {'Mean':>10} {'P95':>10} {'P99':>10}")
            print(f"  {'Cloud':<12} {cloud_stats['min']:>10.3f} {cloud_stats['max']:>10.3f} {cloud_stats['mean']:>10.3f} {cloud_stats['p95']:>10.3f} {cloud_stats['p99']:>10.3f}")
        
        self.report.add_test_result(
            test_name=f'Cold Start ({mode})',
            test_type='performance',
            success=True,
            duration=sum(total_times),
            metrics={
                'Avg Total': f"{total_stats['mean']:.3f}s",
                'P95': f"{total_stats['p95']:.3f}s",
                'P99': f"{total_stats['p99']:.3f}s",
                # 新增：网络 RTT 基线
                'Avg RTT Baseline': f"{rtt_stats['mean']:.3f}s" if rtt_stats else 'N/A',
                'P95 RTT Baseline': f"{rtt_stats['p95']:.3f}s" if rtt_stats else 'N/A',
                # 新增：云平台内部耗时
                'Avg Cloud Internal': f"{cloud_stats['mean']:.3f}s" if cloud_stats else 'N/A',
                'P95 Cloud Internal': f"{cloud_stats['p95']:.3f}s" if cloud_stats else 'N/A',
            }
        )
        return {'success': True, 'stats': total_stats, 'rtt_stats': rtt_stats, 'cloud_stats': cloud_stats}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Cold Start Test")
    parser.add_argument("-n", "--runs", type=int, default=10)
    parser.add_argument("-c", "--count", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--mode", choices=["sequential", "concurrent", "both"], default="both")
    parser.add_argument("--template", type=str, default=None)
    args = parser.parse_args()
    
    template = args.template or os.environ.get("CUBE_TEMPLATE_ID", "base")
    if not os.environ.get("E2B_API_KEY"):
        print("Error: E2B_API_KEY not set")
        sys.exit(1)
    
    report = ReportGenerator()
    test = ColdStartTest(template=template, report=report)
    
    if args.mode in ["sequential", "both"]:
        test.run_sequential_test(runs=args.runs)
    if args.mode in ["concurrent", "both"]:
        test.run_concurrent_test(count=args.count, concurrency=args.concurrency)
    
    report.save("cold_start_report.html")


if __name__ == "__main__":
    main()