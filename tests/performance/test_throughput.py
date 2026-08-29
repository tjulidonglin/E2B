"""
Performance Test - Throughput Testing

Tests the throughput of E2B sandbox operations including:
- Concurrent sandbox creation
- Command execution throughput
- Mixed operation throughput
"""

import os
import sys
import time
import argparse
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from e2b_code_interpreter import Sandbox
except ImportError:
    print("Error: e2b_code_interpreter package not installed")
    sys.exit(1)

from utils.sandbox_manager import SandboxManager
from utils.report_generator import ReportGenerator


class ThroughputTest:
    """Tests sandbox throughput under various conditions"""
    
    def __init__(self, template: str, concurrency: int = 50, report: ReportGenerator = None):
        self.template = template
        self.concurrency = concurrency
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
    
    def test_concurrent_creation(self, count: int = None) -> Dict[str, Any]:
        """
        Test concurrent sandbox creation throughput.
        
        Args:
            count: Number of sandboxes to create (defaults to concurrency)
            
        Returns:
            Dictionary with test results
        """
        count = count or self.concurrency
        print(f"\n{'='*60}")
        print(f"  Concurrent Creation Test (N={count})")
        print(f"{'='*60}\n")
        
        start_time = time.perf_counter()
        success_count = 0
        failed_count = 0
        create_times = []
        
        def create_sandbox(idx: int):
            try:
                s = time.perf_counter()
                sbx = self._create_sandbox(timeout=120)
                elapsed = time.perf_counter() - s
                sbx.kill()
                return True, elapsed
            except Exception as e:
                return False, str(e)
        
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = {executor.submit(create_sandbox, i): i for i in range(count)}
            
            for i, future in enumerate(as_completed(futures), 1):
                success, result = future.result()
                if success:
                    success_count += 1
                    create_times.append(result)
                    print(f"  [{i}/{count}] ✓ Sandbox created in {result:.2f}s")
                else:
                    failed_count += 1
                    print(f"  [{i}/{count}] ✗ Failed: {result}")
        
        total_time = time.perf_counter() - start_time
        throughput = success_count / total_time if total_time > 0 else 0
        
        # 计算创建时间的百分位数
        def _percentile(values, p):
            if not values:
                return None
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            if n == 1:
                return sorted_vals[0]
            idx = min(int(n * p), n - 1)
            return sorted_vals[idx]
        
        p95_create = _percentile(create_times, 0.95)
        p99_create = _percentile(create_times, 0.99)
        
        result = {
            'test_name': 'Concurrent Creation Throughput',
            'test_type': 'performance',
            'success': failed_count == 0,
            'duration': total_time,
            'metrics': {
                'Total Sandboxes': count,
                'Success': success_count,
                'Failed': failed_count,
                'Success Rate': f"{success_count/count*100:.1f}%",
                'Throughput': f"{throughput:.2f} sandboxes/s",
                'Avg Create Time': f"{sum(create_times)/len(create_times):.2f}s" if create_times else 'N/A',
                'P95 Create Time': f"{p95_create:.2f}s" if p95_create is not None else 'N/A',
                'P99 Create Time': f"{p99_create:.2f}s" if p99_create is not None else 'N/A',
                'Total Time': f"{total_time:.2f}s",
            },
        }
        
        self.report.add_test_result(**result)
        return result
    
    def test_command_throughput(self, count: int = 10, iterations: int = 100) -> Dict[str, Any]:
        """
        Test command execution throughput in a sandbox.
        
        Args:
            count: Number of sandboxes to use
            iterations: Number of commands to execute per sandbox
            
        Returns:
            Dictionary with test results
        """
        print(f"\n{'='*60}")
        print(f"  Command Throughput Test (N={count}, Iterations={iterations})")
        print(f"{'='*60}\n")
        
        start_time = time.perf_counter()
        total_commands = 0
        success_commands = 0
        failed_commands = 0
        latencies = []
        
        def run_commands(sandbox_idx: int):
            nonlocal total_commands, success_commands, failed_commands
            
            try:
                sbx = self._create_sandbox(timeout=120)
                for i in range(iterations):
                    total_commands += 1
                    cmd_start = time.perf_counter()
                    try:
                        result = sbx.commands.run("echo test", timeout=10)
                        latency = time.perf_counter() - cmd_start
                        latencies.append(latency)
                        success_commands += 1
                    except Exception:
                        failed_commands += 1
                sbx.kill()
                return True
            except Exception:
                return False
        
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(run_commands, i) for i in range(count)]
            for future in as_completed(futures):
                future.result()
        
        total_time = time.perf_counter() - start_time
        throughput = success_commands / total_time if total_time > 0 else 0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        # 计算延迟的百分位数
        def _percentile(values, p):
            if not values:
                return None
            sorted_vals = sorted(values)
            n = len(sorted_vals)
            if n == 1:
                return sorted_vals[0]
            idx = min(int(n * p), n - 1)
            return sorted_vals[idx]
        
        p95_latency = _percentile(latencies, 0.95)
        p99_latency = _percentile(latencies, 0.99)
        
        result = {
            'test_name': 'Command Execution Throughput',
            'test_type': 'performance',
            'success': failed_commands == 0,
            'duration': total_time,
            'metrics': {
                'Total Commands': total_commands,
                'Success': success_commands,
                'Failed': failed_commands,
                'Throughput': f"{throughput:.2f} commands/s",
                'Avg Latency': f"{avg_latency*1000:.2f}ms",
                'P95 Latency': f"{p95_latency*1000:.2f}ms" if p95_latency is not None else 'N/A',
                'P99 Latency': f"{p99_latency*1000:.2f}ms" if p99_latency is not None else 'N/A',
                'Total Time': f"{total_time:.2f}s",
            },
        }
        
        self.report.add_test_result(**result)
        return result
    
    def generate_report(self, filename: str = None) -> str:
        """Generate HTML report"""
        return self.report.generate_html_report(filename)


def main():
    parser = argparse.ArgumentParser(description="E2B Sandbox Throughput Test")
    parser.add_argument('--count', type=int, default=50, help='Number of sandboxes (default: 50)')
    parser.add_argument('--template', type=str, help='Sandbox template ID')
    parser.add_argument('--output', type=str, help='Report output filename')
    args = parser.parse_args()
    
    template = args.template or os.environ.get("CUBE_TEMPLATE_ID")
    if not template:
        print("Error: Template ID required. Set CUBE_TEMPLATE_ID or use --template")
        sys.exit(1)
    
    test = ThroughputTest(template=template, concurrency=args.count)
    
    # Run concurrent creation test
    test.test_concurrent_creation(count=args.count)
    
    # Generate report
    report_path = test.generate_report(args.output)
    print(f"\n\n{'='*60}")
    print(f"  Report generated: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()