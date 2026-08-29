"""
Security Test - Network Isolation

Tests network isolation of E2B sandboxes.
Verifies that sandboxes are isolated from external network access.
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


class NetworkIsolationTest:
    """Tests network isolation for E2B sandboxes"""
    
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
    
    def test_external_http_access(self) -> Dict[str, Any]:
        """Test if sandbox can access external HTTP endpoints"""
        print(f"\n{'='*60}")
        print(f"  Testing External HTTP Access")
        print(f"{'='*60}\n")
        
        sbx = self._create_sandbox(timeout=120)
        
        test_cases = [
            ("http://www.google.com", "HTTP to Google"),
            ("http://www.baidu.com", "HTTP to Baidu"),
            ("https://www.google.com", "HTTPS to Google"),
            ("https://api.ipify.org?format=json", "Public IP API"),
        ]
        
        results = []
        
        try:
            for url, description in test_cases:
                print(f"  Testing: {description} ({url})")
                
                # Try using curl to access the URL
                result = sbx.commands.run(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 5 {url} 2>&1", timeout=10)
                
                can_access = False
                if result.exit_code == 0 and result.stdout:
                    # Check if we got a valid HTTP response
                    http_code = result.stdout.strip()
                    can_access = http_code.isdigit() and int(http_code) < 500
                
                test_result = {
                    'url': url,
                    'description': description,
                    'can_access': can_access,
                    'exit_code': result.exit_code,
                    'output': result.stdout[:100] if result.stdout else '',
                }
                results.append(test_result)
                
                status = "⚠️  ACCESSIBLE" if can_access else "✓ BLOCKED"
                print(f"    {status}")
        
        finally:
            from utils.huawei_patch import safe_kill_sandbox
            safe_kill_sandbox(sbx)
        
        # Determine if test passed (all should be blocked for security)
        all_blocked = all(not r['can_access'] for r in results)
        
        self.report.add_test_result(
            test_name='External Network Access Test',
            test_type='security',
            success=all_blocked,
            duration=0,
            metrics={
                'Total Tests': len(results),
                'Blocked': sum(1 for r in results if not r['can_access']),
                'Accessible': sum(1 for r in results if r['can_access']),
            },
            error="Some endpoints are accessible" if not all_blocked else None,
        )
        
        return {
            'success': all_blocked,
            'results': results,
        }
    
    def test_dns_resolution(self) -> Dict[str, Any]:
        """Test if sandbox can resolve external DNS"""
        print(f"\n{'='*60}")
        print(f"  Testing DNS Resolution")
        print(f"{'='*60}\n")
        
        sbx = self._create_sandbox(timeout=120)
        
        domains = ["google.com", "github.com", "example.com"]
        results = []
        
        try:
            for domain in domains:
                print(f"  Testing: {domain}")
                
                result = sbx.commands.run(f"nslookup {domain} 2>&1 || host {domain} 2>&1", timeout=10)
                
                can_resolve = result.exit_code == 0 and "address" in result.stdout.lower()
                
                results.append({
                    'domain': domain,
                    'can_resolve': can_resolve,
                })
                
                status = "⚠️  RESOLVABLE" if can_resolve else "✓ BLOCKED"
                print(f"    {status}")
        
        finally:
            sbx.kill()
        
        all_blocked = all(not r['can_resolve'] for r in results)
        
        self.report.add_test_result(
            test_name='DNS Resolution Test',
            test_type='security',
            success=all_blocked,
            duration=0,
            metrics={
                'Domains Tested': len(domains),
                'Blocked': sum(1 for r in results if not r['can_resolve']),
            }
        )
        
        return {'success': all_blocked, 'results': results}
    
    def generate_report(self, filename: str = None) -> str:
        """Generate HTML report"""
        return self.report.generate_html_report(filename)


def main():
    parser = argparse.ArgumentParser(description="E2B Sandbox Network Isolation Test")
    parser.add_argument('--template', type=str, help='Sandbox template ID')
    parser.add_argument('--output', type=str, help='Report output filename')
    args = parser.parse_args()
    
    template = args.template or os.environ.get("CUBE_TEMPLATE_ID")
    if not template:
        print("Error: Template ID required. Set CUBE_TEMPLATE_ID or use --template")
        sys.exit(1)
    
    test = NetworkIsolationTest(template=template)
    test.test_external_http_access()
    test.test_dns_resolution()
    
    report_path = test.generate_report(args.output)
    print(f"\n{'='*60}")
    print(f"  Report generated: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()