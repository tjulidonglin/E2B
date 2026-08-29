"""
Report Generator - Generates HTML test reports
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


class ReportGenerator:
    """
    Generates HTML test reports with detailed statistics and visualizations.
    """
    
    def __init__(self, output_dir: str = "reports"):
        """
        Initialize ReportGenerator.
        
        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self._test_results: List[Dict[str, Any]] = []
        self._metadata: Dict[str, Any] = {}
    
    def add_test_result(
        self,
        test_name: str,
        test_type: str,
        success: bool,
        duration: float,
        metrics: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        Add a test result to the report.
        
        Args:
            test_name: Name of the test
            test_type: Type of test (performance/security)
            success: Whether the test passed
            duration: Duration of the test in seconds
            metrics: Performance metrics
            details: Additional test details
            error: Error message if test failed
        """
        result = {
            "test_name": test_name,
            "test_type": test_type,
            "success": success,
            "duration": duration,
            "metrics": metrics or {},
            "details": details or {},
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }
        self._test_results.append(result)
    
    def set_metadata(self, metadata: Dict[str, Any]):
        """Set metadata for the report"""
        self._metadata.update(metadata)
    
    def generate_html_report(self, filename: Optional[str] = None) -> str:
        """
        Generate HTML report.
        
        Args:
            filename: Custom filename for the report
            
        Returns:
            Path to the generated HTML file
        """
        if not filename:
            filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        filepath = self.output_dir / filename
        
        html_content = self._generate_html()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(filepath)
    
    def _generate_html(self) -> str:
        """Generate HTML content for the report"""
        summary = self._calculate_summary()
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E2B Sandbox Test Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; background: #f5f5f5; color: #333; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 20px; margin-bottom: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ font-size: 1.1em; opacity: 0.9; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .card h3 {{ color: #667eea; margin-bottom: 10px; font-size: 1.2em; }}
        .card .value {{ font-size: 2.5em; font-weight: bold; color: #333; }}
        .card.success .value {{ color: #10b981; }}
        .card.failed .value {{ color: #ef4444; }}
        .card.info .value {{ color: #3b82f6; }}
        .section {{ background: white; padding: 30px; margin-bottom: 30px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .section h2 {{ color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #667eea; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; color: #374151; font-weight: 600; }}
        tr:hover {{ background: #f9fafb; }}
        .status-pass {{ color: #10b981; font-weight: bold; }}
        .status-fail {{ color: #ef4444; font-weight: bold; }}
        .metrics {{ margin-top: 10px; }}
        .metrics dt {{ font-weight: bold; color: #667eea; }}
        .metrics dd {{ margin-left: 0; margin-bottom: 8px; color: #666; }}
        .progress {{ background: #e5e7eb; border-radius: 9999px; height: 8px; overflow: hidden; margin-top: 5px; }}
        .progress-bar {{ height: 100%; border-radius: 9999px; }}
        .progress-bar.success {{ background: #10b981; }}
        .progress-bar.failed {{ background: #ef4444; }}
        .timestamp {{ color: #9ca3af; font-size: 0.9em; }}
        .error-msg {{ background: #fee2e2; border: 1px solid #fecaca; border-radius: 5px; padding: 10px; margin-top: 10px; color: #dc2626; font-family: monospace; font-size: 0.9em; }}
        
        /* 交互样式 */
        .test-row {{ transition: background-color 0.2s; }}
        .test-row:hover {{ background: #e5e7eb; }}
        .test-details {{ background: #f9fafb; }}
        .test-details td {{ padding: 20px; border-bottom: 2px solid #e5e7eb; }}
        .detail-section {{ margin-bottom: 15px; padding: 15px; background: white; border-radius: 8px; border-left: 4px solid #667eea; }}
        .detail-section h4 {{ color: #374151; margin-bottom: 10px; font-size: 1.1em; }}
        .detail-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        .detail-table th, .detail-table td {{ padding: 8px 12px; border: 1px solid #e5e7eb; }}
        .detail-table th {{ background: #f9fafb; color: #374151; }}
        .detail-table td {{ color: #666; }}
        .error-text {{ background: #fee2e2; border: 1px solid #fecaca; border-radius: 5px; padding: 15px; color: #dc2626; font-family: 'Courier New', monospace; font-size: 0.9em; white-space: pre-wrap; max-height: 400px; overflow-y: auto; }}
        .btn-details {{ background: #667eea; color: white; border: none; padding: 6px 12px; border-radius: 5px; cursor: pointer; font-size: 0.85em; transition: background 0.2s; }}
        .btn-details:hover {{ background: #5568d3; }}
        .btn-details.expanded {{ background: #764ba2; }}
    </style>
    
    <script>
        function toggleDetails(detailsId) {{
            const detailsRow = document.getElementById(detailsId);
            if (!detailsRow) return;
            
            const isVisible = detailsRow.style.display !== 'none';
            detailsRow.style.display = isVisible ? 'none' : 'table-row';
            
            // 更新所有展开按钮的状态
            document.querySelectorAll('.btn-details').forEach(btn => {{
                const target = btn.getAttribute('data-target');
                if (target === detailsId) {{
                    btn.textContent = isVisible ? '查看详情' : '收起详情';
                    btn.classList.toggle('expanded', !isVisible);
                }}
            }});
        }}
        
        // 页面加载后，自动展开失败的测试详情
        document.addEventListener('DOMContentLoaded', function() {{
            const failedTests = document.querySelectorAll('.status-fail');
            failedTests.forEach(row => {{
                const detailsId = 'test-details-' + (Array.from(document.querySelectorAll('.test-row')).indexOf(row) || 0);
                const detailsRow = document.getElementById(detailsId);
                if (detailsRow) {{
                    detailsRow.style.display = 'table-row';
                    const btn = document.querySelector('.btn-details[data-target="' + detailsId + '"]');
                    if (btn) {{
                        btn.textContent = '收起详情';
                        btn.classList.add('expanded');
                    }}
                }}
            }});
        }});
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 E2B Sandbox Test Report</h1>
            <p>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="card info">
                <h3>Total Tests</h3>
                <div class="value">{summary['total']}</div>
            </div>
            <div class="card success">
                <h3>Passed</h3>
                <div class="value">{summary['passed']}</div>
            </div>
            <div class="card failed">
                <h3>Failed</h3>
                <div class="value">{summary['failed']}</div>
            </div>
            <div class="card info">
                <h3>Pass Rate</h3>
                <div class="value">{summary['pass_rate']:.1f}%</div>
                <div class="progress">
                    <div class="progress-bar {'success' if summary['pass_rate'] >= 80 else 'failed'}" style="width: {summary['pass_rate']}%"></div>
                </div>
            </div>
            <div class="card info">
                <h3>Duration</h3>
                <div class="value">{summary['total_duration']:.2f}s</div>
            </div>
        </div>
"""
        
        # Add performance tests section
        performance_tests = [r for r in self._test_results if r['test_type'] == 'performance']
        if performance_tests:
            html += self._generate_test_section("Performance Tests", performance_tests)
        
        # Add security tests section
        security_tests = [r for r in self._test_results if r['test_type'] == 'security']
        if security_tests:
            html += self._generate_test_section("Security Tests", security_tests)
        
        # Add metadata section if exists
        if self._metadata:
            html += """
        <div class="section">
            <h2>📋 Test Configuration</h2>
            <table>
"""
            for key, value in self._metadata.items():
                html += f"                <tr><th>{key}</th><td>{value}</td></tr>\n"
            html += """            </table>
        </div>
"""
        
        html += """
    </div>
</body>
</html>"""
        
        return html
    
    def _generate_test_section(self, title: str, tests: List[Dict]) -> str:
        """Generate HTML for a test section"""
        html = f"""
        <div class="section">
            <h2>🧪 {title}</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Details</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
"""
        for idx, test in enumerate(tests):
            status_class = "status-pass" if test['success'] else "status-fail"
            status_text = "✓ PASS" if test['success'] else "✗ FAIL"
            row_id = f"test-row-{idx}"
            details_id = f"test-details-{idx}"
            
            html += f"""
                    <tr class="test-row" onclick="toggleDetails('{details_id}')" style="cursor: pointer;">
                        <td>{test['test_name']}</td>
                        <td class="{status_class}">{status_text}</td>
                        <td>{test['duration']:.3f}s</td>
                        <td>
                            <span class="timestamp">{test['timestamp']}</span>
"""
            
            if test['metrics']:
                html += '<dl class="metrics">'
                for key, value in test['metrics'].items():
                    html += f'<dt>{key}:</dt><dd>{value}</dd>'
                html += '</dl>'
            
            if test['error']:
                html += f'<div class="error-msg">{test["error"]}</div>'
            
            html += f"""
                        </td>
                        <td><button class="btn-details" data-target="{details_id}">查看详情</button></td>
                    </tr>
                    <tr class="test-details" id="{details_id}" style="display: none;">
                        <td colspan="4">
"""
            
            # 添加详情区域
            if test.get('details'):
                html += '<div class="detail-section"><h4>📝 测试详情</h4><dl class="metrics">'
                for key, value in test['details'].items():
                    html += f'<dt>{key}:</dt><dd>{value}</dd>'
                html += '</dl></div>'
            
            if test.get('error'):
                html += f'<div class="detail-section"><h4>❌ 错误信息</h4><pre class="error-text">{test["error"]}</pre></div>'
            
            if test.get('metrics'):
                html += f'<div class="detail-section"><h4>📊 性能指标</h4><dl class="metrics">'
                for key, value in test['metrics'].items():
                    html += f'<dt>{key}:</dt><dd>{value}</dd>'
                html += '</dl></div>'
            
            # 如果是性能测试，添加详细数据表格
            if test.get('test_type') == 'performance' and test.get('metrics'):
                html += '<div class="detail-section"><h4>📋 详细数据</h4><table class="detail-table"><thead><tr>'
                for key in test['metrics'].keys():
                    html += f'<th>{key}</th>'
                html += '</tr></thead><tbody><tr>'
                for value in test['metrics'].values():
                    html += f'<td>{value}</td>'
                html += '</tr></tbody></table></div>'
            
            html += """
                        </td>
                    </tr>
"""
        
        html += """
                </tbody>
            </table>
        </div>
"""
        return html
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate test summary statistics"""
        total = len(self._test_results)
        passed = sum(1 for r in self._test_results if r['success'])
        failed = total - passed
        total_duration = sum(r['duration'] for r in self._test_results)
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': pass_rate,
            'total_duration': total_duration,
        }
    
    def to_json(self) -> str:
        """Export test results as JSON"""
        data = {
            'metadata': self._metadata,
            'summary': self._calculate_summary(),
            'results': self._test_results,
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def save(self, filename: str = "test_report.html") -> str:
        """
        Save the report to a file.
        
        Args:
            filename: Filename for the report
            
        Returns:
            Path to the saved file
        """
        return self.generate_html_report(filename)
    
    def clear(self):
        """Clear all test results"""
        self._test_results = []
        self._metadata = {}