"""
Performance Test - Resource Utilization Monitoring

Monitors resource usage (CPU, Memory, Disk) of E2B sandboxes.
"""

import os
import sys
import time
import argparse
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from e2b_code_interpreter import Sandbox
except ImportError:
    print("Error: e2b_code_interpreter package not installed")
    sys.exit(1)

from utils.metrics_collector import MetricsCollector
from utils.report_generator import ReportGenerator


class ResourceMonitorTest:
    """Monitors sandbox resource utilization"""
    
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
    
    def monitor_idle_sandbox(self, duration: int = 60, interval: int = 5) -> Dict[str, Any]:
        """
        Monitor resource usage of an idle sandbox.
        
        Args:
            duration: Monitoring duration in seconds
            interval: Sampling interval in seconds
            
        Returns:
            Monitoring results
        """
        print(f"\n{'='*60}")
        print(f"  Idle Sandbox Resource Monitoring")
        print(f"  Duration: {duration}s, Interval: {interval}s")
        print(f"{'='*60}\n")
        
        sbx = self._create_sandbox(timeout=120)
        collector = MetricsCollector(sbx)
        metrics_list = []
        
        print(f"  {'Time':<10} {'CPU%':<10} {'Mem%':<10} {'Disk%':<10}")
        print(f"  {'-'*40}")
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                metrics = collector.collect()
                metrics_list.append(metrics)
                
                elapsed = int(time.time() - start_time)
                print(f"  {elapsed}s         {metrics.cpu_percent:.1f}%      {metrics.memory_percent:.1f}%      {metrics.disk_percent:.1f}%")
                
                time.sleep(interval)
        
        finally:
            sbx.kill()
        
        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in metrics_list) / len(metrics_list)
        avg_mem = sum(m.memory_percent for m in metrics_list) / len(metrics_list)
        avg_disk = sum(m.disk_percent for m in metrics_list) / len(metrics_list)
        
        result = {
            'duration': duration,
            'samples': len(metrics_list),
            'avg_cpu_percent': avg_cpu,
            'avg_memory_percent': avg_mem,
            'avg_disk_percent': avg_disk,
        }
        
        self.report.add_test_result(
            test_name='Idle Sandbox Resource Usage',
            test_type='performance',
            success=True,
            duration=duration,
            metrics={
                'Duration': f"{duration}s",
                'Samples': len(metrics_list),
                'Avg CPU': f"{avg_cpu:.1f}%",
                'Avg Memory': f"{avg_mem:.1f}%",
                'Avg Disk': f"{avg_disk:.1f}%",
            }
        )
        
        return result
    
    def monitor_under_load(self, load_type: str = 'cpu', duration: int = 30) -> Dict[str, Any]:
        """
        Monitor resource usage under load.
        
        Args:
            load_type: Type of load ('cpu', 'memory', 'disk')
            duration: Test duration in seconds
            
        Returns:
            Monitoring results
        """
        print(f"\n{'='*60}")
        print(f"  Resource Monitoring Under {load_type.upper()} Load")
        print(f"{'='*60}\n")
        
        sbx = self._create_sandbox(timeout=120)
        collector = MetricsCollector(sbx)
        
        # Start load generation
        if load_type == 'cpu':
            load_cmd = "while true; do :; done &"
        elif load_type == 'memory':
            load_cmd = "dd if=/dev/zero of=/tmp/bigfile bs=1M count=100"
        else:
            load_cmd = "echo 'no load'"
        
        try:
            sbx.commands.run(load_cmd, timeout=5)
            
            metrics_list = []
            start_time = time.time()
            
            while time.time() - start_time < duration:
                metrics = collector.collect()
                metrics_list.append(metrics)
                time.sleep(2)
        
        finally:
            sbx.kill()
        
        avg_cpu = sum(m.cpu_percent for m in metrics_list) / len(metrics_list)
        avg_mem = sum(m.memory_percent for m in metrics_list) / len(metrics_list)
        
        result = {
            'load_type': load_type,
            'duration': duration,
            'avg_cpu': avg_cpu,
            'avg_memory': avg_mem,
        }
        
        self.report.add_test_result(
            test_name=f'Resource Usage Under {load_type.upper()} Load',
            test_type='performance',
            success=True,
            duration=duration,
            metrics={
                'Load Type': load_type,
                'Avg CPU': f"{avg_cpu:.1f}%",
                'Avg Memory': f"{avg_mem:.1f}%",
            }
        )
        
        return result
    
    def generate_report(self, filename: str = None) -> str:
        """Generate HTML report"""
        return self.report.generate_html_report(filename)


def main():
    parser = argparse.ArgumentParser(description="E2B Sandbox Resource Monitor")
    parser.add_argument('--duration', type=int, default=60, help='Monitoring duration (seconds)')
    parser.add_argument('--interval', type=int, default=5, help='Sampling interval (seconds)')
    parser.add_argument('--template', type=str, help='Sandbox template ID')
    parser.add_argument('--output', type=str, help='Report output filename')
    args = parser.parse_args()
    
    template = args.template or os.environ.get("CUBE_TEMPLATE_ID")
    if not template:
        print("Error: Template ID required. Set CUBE_TEMPLATE_ID or use --template")
        sys.exit(1)
    
    test = ResourceMonitorTest(template=template)
    test.monitor_idle_sandbox(duration=args.duration, interval=args.interval)
    
    report_path = test.generate_report(args.output)
    print(f"\n{'='*60}")
    print(f"  Report generated: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()