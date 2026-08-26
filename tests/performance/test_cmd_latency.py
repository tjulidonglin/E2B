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
    
    def test_single_command(self, command: str, iterations: int = 100) -> Dict[str, Any]:
        """
        Test latency of a single command.
        
        Args:
            command: Command to test
            iterations: Number of iterations
            
        Returns:
            Test results dictionary
        """
        print(f"\n  Testing: {command}")
        
        sbx = Sandbox.create(template=self.template, timeout=120)
        latencies = []
        
        try:
            for i in range(iterations):
                start = time.perf_counter()
                result = sbx.commands.run(command, timeout=10)
                latency = time.perf_counter() - start
                latencies.append(latency * 1000)  # Convert to ms
                
                if (i + 1) % 10 == 0:
                    print(f"    [{i+1}/{iterations}] Latency: {latency*1000:.2f}ms")
        
        finally:
            sbx.kill()
        
        # Calculate statistics
        avg = statistics.mean(latencies)
        min_val = min(latencies)
        max_val = max(latencies)
        median = statistics.median(latencies)
        stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0
        
        return {
            'command': command,
            'iterations': iterations,
            'avg_ms': avg,
            'min_ms': min_val,
            'max_ms': max_val,
            'median_ms': median,
            'stdev_ms': stdev,
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
                    'Std Dev': f"{result['stdev_ms']:.2f}ms",
                }
            )
        
        total_time = time.perf_counter() - overall_start
        print(f"\n{'='*60}")
        print(f"  Summary")
        print(f"{'='*60}")
        print(f"  Total Commands Tested: {len(results)}")
        print(f"  Total Time: {total_time:.2f}s")
        
        # Print results table
        print(f"\n  {'Command':<20} {'Avg':<12} {'Min':<12} {'Max':<12} {'Median':<12}")
        print(f"  {'-'*68}")
        for r in results:
            print(f"  {r['command']:<20} {r['avg_ms']:.2f}ms      {r['min_ms']:.2f}ms      {r['max_ms']:.2f}ms      {r['median_ms']:.2f}ms")
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