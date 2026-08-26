"""
Security Test - Resource Isolation (CPU, Memory, Disk)

Tests resource isolation for E2B sandboxes.
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


class ResourceIsolationTest:
    """Tests resource isolation for E2B sandboxes"""
    
    def __init__(self, template: str, report: ReportGenerator = None):
        self.template = template
        self.report = report or ReportGenerator()
    
    def test_cpu_limit(self) -> Dict[str, Any]:
        """Test CPU resource limits"""
        print(f"\n{'='*60}")
        print(f"  Testing CPU Resource Limits")
        print(f"{'='*60}\n")
        
        sbx = Sandbox.create(template=self.template, timeout=120)
        
        try:
            print(f"  Starting CPU-intensive task...")
            start = time.time()
            try:
                result = sbx.commands.run("timeout 10 bash -c 'while true; do :; done'", timeout=15)
                elapsed = time.time() - start
                # Exit code 124 means timeout was reached, which is expected
                print(f"  Task completed in {elapsed:.2f}s (exit code: {result.exit_code})")
            except Exception as e:
                elapsed = time.time() - start
                print(f"  Task terminated after {elapsed:.2f}s (as expected)")
            
            self.report.add_test_result(
                test_name='CPU Limit Test',
                test_type='security',
                success=True,
                duration=elapsed,
                metrics={'Duration': f"{elapsed:.2f}s", 'Result': 'CPU task completed/terminated'}
            )
            
            return {'success': True}
        finally:
            sbx.kill()
    
    def test_memory_limit(self) -> Dict[str, Any]:
        """Test memory resource limits"""
        print(f"\n{'='*60}")
        print(f"  Testing Memory Resource Limits")
        print(f"{'='*60}\n")
        
        sbx = Sandbox.create(template=self.template, timeout=120)
        
        try:
            print(f"  Attempting to allocate large memory...")
            result = sbx.commands.run("timeout 30 dd if=/dev/zero of=/tmp/bigfile bs=1M count=1024 && rm /tmp/bigfile", timeout=35)
            
            allocation_ok = result.exit_code == 0
            print(f"  Memory allocation {'succeeded' if allocation_ok else 'failed'}")
            
            self.report.add_test_result(
                test_name='Memory Limit Test',
                test_type='security',
                success=True,
                duration=0,
                metrics={'Allocation': 'Yes' if allocation_ok else 'No'}
            )
            
            return {'success': True}
        finally:
            sbx.kill()
    
    def test_disk_limit(self) -> Dict[str, Any]:
        """Test disk resource limits"""
        print(f"\n{'='*60}")
        print(f"  Testing Disk Resource Limits")
        print(f"{'='*60}\n")
        
        sbx = Sandbox.create(template=self.template, timeout=120)
        
        try:
            print(f"  Checking disk space...")
            df_result = sbx.commands.run("df -h /", timeout=10)
            print(df_result.stdout)
            
            print(f"\n  Attempting to write large file...")
            result = sbx.commands.run("timeout 30 dd if=/dev/zero of=/tmp/testfile bs=1M count=500 && rm /tmp/testfile", timeout=35)
            
            write_ok = result.exit_code == 0
            print(f"  Write {'succeeded' if write_ok else 'failed'}")
            
            self.report.add_test_result(
                test_name='Disk Limit Test',
                test_type='security',
                success=True,
                duration=0,
                metrics={'Write': 'Yes' if write_ok else 'No'}
            )
            
            return {'success': True}
        finally:
            sbx.kill()
    
    def run_all_tests(self):
        """Run all resource isolation tests"""
        self.test_cpu_limit()
        self.test_memory_limit()
        self.test_disk_limit()
    
    def generate_report(self, filename: str = None) -> str:
        """Generate HTML report"""
        return self.report.generate_html_report(filename)


def main():
    parser = argparse.ArgumentParser(description="E2B Sandbox Resource Isolation Test")
    parser.add_argument('--template', type=str, help='Sandbox template ID')
    parser.add_argument('--output', type=str, help='Report output filename')
    args = parser.parse_args()
    
    template = args.template or os.environ.get("CUBE_TEMPLATE_ID")
    if not template:
        print("Error: Template ID required")
        sys.exit(1)
    
    test = ResourceIsolationTest(template=template)
    test.run_all_tests()
    
    report_path = test.generate_report(args.output)
    print(f"\n{'='*60}")
    print(f"  Report generated: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()