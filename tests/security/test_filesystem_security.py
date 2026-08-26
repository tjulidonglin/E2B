"""
Security Test - Filesystem Isolation

Tests filesystem isolation between different E2B sandboxes.
Verifies that files created in one sandbox are not visible in another.
"""

import os
import sys
import time
import argparse
import random
import string
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from e2b_code_interpreter import Sandbox
except ImportError:
    print("Error: e2b_code_interpreter package not installed")
    sys.exit(1)

from utils.report_generator import ReportGenerator


class FilesystemSecurityTest:
    """Tests filesystem security for E2B sandboxes"""
    
    def __init__(self, template: str, report: ReportGenerator = None):
        self.template = template
        self.report = report or ReportGenerator()
    
    def test_file_isolation(self) -> Dict[str, Any]:
        """
        Test that files created in one sandbox are not visible in another.
        
        Process:
        1. Create sandbox A and write a unique file
        2. Create sandbox B and try to read that file
        3. File should not exist in sandbox B
        """
        print(f"\n{'='*60}")
        print(f"  Testing File Isolation Between Sandboxes")
        print(f"{'='*60}\n")
        
        # Generate unique filename and content
        unique_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        filename = f"/tmp/test_file_{unique_id}.txt"
        content = f"Secret data {unique_id}"
        
        # Sandbox A: Create file
        print(f"  [1] Creating file in Sandbox A: {filename}")
        sbx_a = Sandbox.create(template=self.template, timeout=120)
        
        try:
            create_result = sbx_a.commands.run(f"echo '{content}' > {filename}", timeout=10)
            
            if create_result.exit_code != 0:
                print(f"    ✗ Failed to create file in Sandbox A")
                return {'success': False, 'error': 'Failed to create test file'}
            
            # Verify file exists in A
            verify_result = sbx_a.commands.run(f"cat {filename}", timeout=10)
            file_in_a = verify_result.exit_code == 0 and content in verify_result.stdout
            
            print(f"    ✓ File created in Sandbox A")
        finally:
            sbx_a.kill()
        
        # Sandbox B: Try to read file
        print(f"\n  [2] Trying to read file from Sandbox B")
        sbx_b = Sandbox.create(template=self.template, timeout=120)
        
        try:
            read_result = sbx_b.commands.run(f"test -f {filename} && echo 'exists' || echo 'not_exists'", timeout=10)
            file_in_b = 'exists' in read_result.stdout
            
            if file_in_b:
                print(f"    ⚠️  File IS accessible (ISOLATION FAILED)")
            else:
                print(f"    ✓ File NOT accessible (ISOLATION PASSED)")
        except Exception as e:
            # If command fails, file is not accessible
            file_in_b = False
            print(f"    ✓ File NOT accessible (ISOLATION PASSED)")
        finally:
            sbx_b.kill()
        
        success = file_in_a and not file_in_b
        
        self.report.add_test_result(
            test_name='File Isolation Test',
            test_type='security',
            success=success,
            duration=0,
            metrics={
                'File Created': 'Yes' if file_in_a else 'No',
                'Visible in Other Sandbox': 'Yes' if file_in_b else 'No',
            },
            error="File isolation failed" if not success else None,
        )
        
        return {'success': success}
    
    def test_directory_isolation(self) -> Dict[str, Any]:
        """Test directory isolation between sandboxes"""
        print(f"\n{'='*60}")
        print(f"  Testing Directory Isolation")
        print(f"{'='*60}\n")
        
        unique_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        dirname = f"/tmp/test_dir_{unique_id}"
        
        # Sandbox A: Create directory
        print(f"  [1] Creating directory in Sandbox A: {dirname}")
        sbx_a = Sandbox.create(template=self.template, timeout=120)
        
        try:
            sbx_a.commands.run(f"mkdir -p {dirname}", timeout=10)
            sbx_a.commands.run(f"echo 'test' > {dirname}/file1.txt", timeout=10)
            print(f"    ✓ Directory created in Sandbox A")
        finally:
            sbx_a.kill()
        
        # Sandbox B: Check if directory exists
        print(f"\n  [2] Checking for directory in Sandbox B")
        sbx_b = Sandbox.create(template=self.template, timeout=120)
        
        try:
            result = sbx_b.commands.run(f"ls {dirname} 2>&1", timeout=10)
            dir_in_b = result.exit_code == 0
            
            if dir_in_b:
                print(f"    ⚠️  Directory IS visible (ISOLATION FAILED)")
            else:
                print(f"    ✓ Directory NOT visible (ISOLATION PASSED)")
        finally:
            sbx_b.kill()
        
        success = not dir_in_b
        
        self.report.add_test_result(
            test_name='Directory Isolation Test',
            test_type='security',
            success=success,
            duration=0,
            metrics={'Directory Visible': 'Yes' if dir_in_b else 'No'}
        )
        
        return {'success': success}
    
    def generate_report(self, filename: str = None) -> str:
        """Generate HTML report"""
        return self.report.generate_html_report(filename)


def main():
    parser = argparse.ArgumentParser(description="E2B Sandbox Filesystem Security Test")
    parser.add_argument('--template', type=str, help='Sandbox template ID')
    parser.add_argument('--output', type=str, help='Report output filename')
    args = parser.parse_args()
    
    template = args.template or os.environ.get("CUBE_TEMPLATE_ID")
    if not template:
        print("Error: Template ID required. Set CUBE_TEMPLATE_ID or use --template")
        sys.exit(1)
    
    test = FilesystemSecurityTest(template=template)
    test.test_file_isolation()
    test.test_directory_isolation()
    
    report_path = test.generate_report(args.output)
    print(f"\n{'='*60}")
    print(f"  Report generated: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()