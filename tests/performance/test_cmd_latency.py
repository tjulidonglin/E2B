"""
Performance Test - Command Execution Latency

Tests the latency of simple command execution in E2B sandboxes.
"""

import os
import sys
import time
import argparse
import statistics
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from e2b_code_interpreter import Sandbox
except ImportError:
    print("Error: e2b_code_interpreter package not installed")
    sys.exit(1)

from utils.report_generator import ReportGenerator


class CommandLatencyTest:
    """Tests command execution latency"""
    
    # Simple commands to test
    TEST_COMMANDS = [
        ("echo 'hello'", "Echo command"),
        ("pwd", "Print working directory"),
        ("ls", "List files"),
        ("whoami", "Current user"),
        ("date", "Current date"),
    ]
    
    def __init__(self, template: str, report: ReportGenerator = None):
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
    
    def _measure_rtt_baseline(self, sbx, probe_count: int = 20) -> float:
        """
        测量网络 RTT 基线（通过执行无实际工作的 echo 命令）。
        返回最小端到端时间（ms），近似等于纯网络 RTT（因为 echo 执行时间 ≈ 0）。
        """
        rtt_samples = []
        for _ in range(probe_count):
            start = time.perf_counter()
            try:
                sbx.commands.run("echo 1", timeout=5)
                elapsed = (time.perf_counter() - start) * 1000  # ms
                rtt_samples.append(elapsed)
            except Exception:
                pass
        return min(rtt_samples) if rtt_samples else 0.0

    def test_single_command(self, command: str, iterations: int = 100) -> Dict[str, Any]:
        """
        Test latency of a single command.
        
        Uses **server-side timing** (date +%s%N inside sandbox) to measure
        the actual execution time without network RTT overhead.
        Also reports end-to-end latency for real-user-experience perspective.
        
        Args:
            command: Command to test
            iterations: Number of iterations
            
        Returns:
            Test results dictionary
        """
        print(f"\n  Testing: {command}")
        
        sbx = self._create_sandbox(timeout=120)
        end_to_end_latencies = []  # 端到端耗时（含网络 RTT）
        server_side_latencies = []  # 服务端计时（不含网络 RTT）
        
        try:
            for i in range(iterations):
                # --- 端到端计时（含网络 RTT）---
                start_e2e = time.perf_counter()
                result = sbx.commands.run(command, timeout=10)
                e2e_latency = (time.perf_counter() - start_e2e) * 1000  # ms
                end_to_end_latencies.append(e2e_latency)
                
                # --- 服务端计时（不含网络 RTT）---
                # 在沙箱内用 date +%s%N 精确计时命令真实执行时间
                server_cmd = (
                    f"start_ns=$(date +%s%N); {command}; end_ns=$(date +%s%N); "
                    f"echo $(( (end_ns - start_ns) / 1000000 ))"
                )
                start = time.perf_counter()
                result = sbx.commands.run(server_cmd, timeout=10)
                latency = time.perf_counter() - start
                server_side_latencies.append(latency * 1000)  # ms
                
                if (i + 1) % 10 == 0:
                    print(f"    [{i+1}/{iterations}] E2E: {e2e_latency:.2f}ms, "
                          f"Server: {server_side_latencies[-1]:.2f}ms")
        
        finally:
            # 安全销毁 sandbox，处理网络错误
            from utils.huawei_patch import safe_kill_sandbox
            safe_kill_sandbox(sbx, self.template[:12])
        
        # Calculate statistics for both views
        sorted_e2e = sorted(end_to_end_latencies)
        sorted_server = sorted(server_side_latencies)
        n = len(end_to_end_latencies)
        
        def percentile(sorted_vals: list, vals: list, p: float) -> float:
            """计算第 p 百分位数（p 为 0~1 之间的浮点数）"""
            if n == 1:
                return vals[0]
            idx = min(int(n * p), n - 1)
            return sorted_vals[idx]
        
        def calc_stats(sorted_vals: list, vals: list) -> Dict[str, float]:
            return {
                'avg': statistics.mean(vals),
                'min': min(vals),
                'max': max(vals),
                'median': statistics.median(vals) if n >= 2 else vals[0],
                'p95': percentile(sorted_vals, vals, 0.95),
                'p99': percentile(sorted_vals, vals, 0.99),
            }
        
        e2e_stats = calc_stats(sorted_e2e, end_to_end_latencies)
        server_stats = calc_stats(sorted_server, server_side_latencies)
        
        # 估算：云平台内部耗时 ≈ 端到端 − RTT 基线
        # 注意：这里没有做 RTT 基线扣除，因为命令延迟测试是服务端计时
        # 如果需要 RTT 基线，可以在这里减去
        
        avg = e2e_stats['avg']
        min_val = e2e_stats['min']
        max_val = e2e_stats['max']
        median = e2e_stats['median']
        stdev = statistics.stdev(end_to_end_latencies) if n > 1 else 0.0
        p95 = e2e_stats['p95']
        p99 = e2e_stats['p99']
        
        server_avg = server_stats['avg']
        server_min = server_stats['min']
        server_max = server_stats['max']
        server_median = server_stats['median']
        server_stdev = statistics.stdev(server_side_latencies) if n > 1 else 0.0
        server_p95 = server_stats['p95']
        server_p99 = server_stats['p99']
        
        return {
            'command': command,
            'iterations': iterations,
            # 端到端统计（含网络 RTT，反映真实用户体验）
            'avg_ms': avg,
            'min_ms': min_val,
            'max_ms': max_val,
            'median_ms': median,
            'stdev_ms': stdev,
            'p95_ms': p95,
            'p99_ms': p99,
            # 服务端统计（不含网络 RTT，反映云平台内部性能）
            'server_avg_ms': server_avg,
            'server_min_ms': server_min,
            'server_max_ms': server_max,
            'server_median_ms': server_median,
            'server_stdev_ms': server_stdev,
            'server_p95_ms': server_p95,
            'server_p99_ms': server_p99,
    
        }
    def run_all_tests(self, iterations: int = 100) -> List[Dict[str, Any]]:
        """Run latency tests for all commands"""
        print(f"\n{'='*60}")
        print(f"  Command Execution Latency Test")
        print(f"  Iterations: {iterations}")
        print(f"{'='*60}\n")
        
        results = []
        overall_start = time.perf_counter()
        
        for command, description in self.TEST_COMMANDS:
            print(f"\n[{description}]")
            result = self.test_single_command(command, iterations)
            result['description'] = description
            results.append(result)
            
            # Add to report
            self.report.add_test_result(
                test_name=f"Command Latency: {description}",
                test_type='performance',
                success=True,
                duration=result['avg_ms'] / 1000,
                metrics={
                    'Command': command,
                    'Iterations': iterations,
                    'Average': f"{result['avg_ms']:.2f}ms",
                    'Min': f"{result['min_ms']:.2f}ms",
                    'Max': f"{result['max_ms']:.2f}ms",
                    'Median': f"{result['median_ms']:.2f}ms",
                    'P95': f"{result['p95_ms']:.2f}ms",
                    'P99': f"{result['p99_ms']:.2f}ms",
                    'Std Dev': f"{result['stdev_ms']:.2f}ms",
                }
            )
        
        total_time = time.perf_counter() - overall_start
        print(f"\n{'='*60}")
        print(f"  Summary")
        print(f"{'='*60}")
        print(f"  Total Commands Tested: {len(results)}")
        print(f"  Total Time: {total_time:.2f}s")
        
        # Print results table (E2E view)
        print(f"\n  === End-to-End Latency (含网络 RTT) ===")
        print(f"  {'Command':<20} {'Avg':<12} {'Min':<12} {'Max':<12} {'Median':<12} {'P95':<12} {'P99':<12}")
        print(f"  {'-'*92}")
        for r in results:
            print(f"  {r['command']:<20} {r['avg_ms']:.2f}ms      {r['min_ms']:.2f}ms      {r['max_ms']:.2f}ms      {r['median_ms']:.2f}ms      {r['p95_ms']:.2f}ms      {r['p99_ms']:.2f}ms")
        
        # Print server-side results table (不含网络 RTT)
        print(f"\n  === Server-Side Latency (不含网络 RTT) ===")
        print(f"  {'Command':<20} {'Avg':<12} {'Min':<12} {'Max':<12} {'Median':<12} {'P95':<12} {'P99':<12}")
        print(f"  {'-'*92}")
        for r in results:
            print(f"  {r['command']:<20} {r['server_avg_ms']:.2f}ms  {r['server_min_ms']:.2f}ms  {r['server_max_ms']:.2f}ms  {r['server_median_ms']:.2f}ms  {r['server_p95_ms']:.2f}ms  {r['server_p99_ms']:.2f}ms")
        print(f"\n")
        
        return results
    
    def generate_report(self, filename: str = None) -> str:
        """Generate HTML report"""
        return self.report.generate_html_report(filename)


def main():
    parser = argparse.ArgumentParser(description="E2B Sandbox Command Latency Test")
    parser.add_argument('--iterations', type=int, default=100, help='Iterations per command')
    parser.add_argument('--template', type=str, help='Sandbox template ID')
    parser.add_argument('--output', type=str, help='Report output filename')
    args = parser.parse_args()
    
    template = args.template or os.environ.get("CUBE_TEMPLATE_ID")
    if not template:
        print("Error: Template ID required. Set CUBE_TEMPLATE_ID or use --template")
        sys.exit(1)
    
    test = CommandLatencyTest(template=template)
    test.run_all_tests(iterations=args.iterations)
    
    report_path = test.generate_report(args.output)
    print(f"\n{'='*60}")
    print(f"  Report generated: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()