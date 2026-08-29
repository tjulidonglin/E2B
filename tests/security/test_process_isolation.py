"""
Security Test - Process Isolation

Tests process isolation between different E2B sandboxes.
Verifies that processes in one sandbox are not visible in another.
"""

import os
import sys
import time
import argparse
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from e2b_code_interpreter import Sandbox
except ImportError:
    print("Error: e2b_code_interpreter package not installed")
    sys.exit(1)

from utils.report_generator import ReportGenerator


class ProcessIsolationTest:
    """Tests process isolation for E2B sandboxes"""
    
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
    
    def test_process_visibility(self) -> Dict[str, Any]:
        """
        Test that processes from one sandbox are not visible in another.
        """
        print(f"\n{'='*60}")
        print(f"  Testing Process Isolation Between Sandboxes")
        print(f"{'='*60}\n")
        
        unique_marker = "UNIQUEPROCESS123"
        
        # Sandbox A: Start a process
        print(f"  [1] Starting unique process in Sandbox A")
        sbx_a = self._create_sandbox(timeout=120)
        
        try:
            # Start a background process
            result = sbx_a.commands.run(f"nohup sleep 60 > /dev/null 2>&1 &", timeout=10)
            
            # Get process list from A
            ps_result = sbx_a.commands.run("ps aux", timeout=10)
            print(f"    ✓ Process started in Sandbox A")
            print(f"    Processes in A: {len(ps_result.stdout.split(chr(10)))} lines")
        
        finally:
            from utils.huawei_patch import safe_kill_sandbox
            safe_kill_sandbox(sbx_a, "A")
        
        # Sandbox B: Check for processes from A
        print(f"\n  [2] Checking for processes in Sandbox B")
        sbx_b = self._create_sandbox(timeout=120)
        
        try:
            ps_result = sbx_b.commands.run("ps aux", timeout=10)
            
            # Check if sleep process from A is visible
            sleep_visible = 'sleep 60' in ps_result.stdout
            
            if sleep_visible:
                print(f"    ⚠️  Process from A IS visible (ISOLATION FAILED)")
            else:
                print(f"    ✓ Process from A NOT visible (ISOLATION PASSED)")
        finally:
            from utils.huawei_patch import safe_kill_sandbox
            safe_kill_sandbox(sbx_b, "B")
        
        success = not sleep_visible
        
        self.report.add_test_result(
            test_name='Process Isolation Test',
            test_type='security',
            success=success,
            duration=0,
            metrics={
                'Process Visible in Other Sandbox': 'Yes' if sleep_visible else 'No',
            },
            error="Process isolation failed" if not success else None,
        )
        
        return {'success': success}
    
    def generate_report(self, filename: str = None) -> str:
        """Generate HTML report"""
        return self.report.generate_html_report(filename)


def main():
    parser = argparse.ArgumentParser(description="E2B Sandbox Process Isolation Test")
    parser.add_argument('--template', type=str, help='Sandbox template ID')
    parser.add_argument('--output', type=str, help='Report output filename')
    args = parser.parse_args()
    
    template = args.template or os.environ.get("CUBE_TEMPLATE_ID")
    if not template:
        print("Error: Template ID required. Set CUBE_TEMPLATE_ID or use --template")
        sys.exit(1)
    
    test = ProcessIsolationTest(template=template)
    test.test_process_visibility()
    
    report_path = test.generate_report(args.output)
    print(f"\n{'='*60}")
    print(f"  Report generated: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()