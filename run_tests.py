#!/usr/bin/env python3
"""
E2B Sandbox Test Runner

Unified entry point for running all E2B sandbox tests.
Generates a single HTML report with all test results.
"""

import os
import sys
import argparse
import time
from datetime import datetime
from pathlib import Path

# Add tests directory to path
sys.path.insert(0, str(Path(__file__).parent / "tests"))

try:
    from e2b_code_interpreter import Sandbox
except ImportError:
    print("Error: e2b_code_interpreter package not installed")
    sys.exit(1)

from tests.utils.report_generator import ReportGenerator
from tests.performance.test_cold_start import ColdStartTest
from tests.performance.test_throughput import ThroughputTest
from tests.performance.test_cmd_latency import CommandLatencyTest
from tests.performance.test_resource_monitor import ResourceMonitorTest
from tests.security.test_network_isolation import NetworkIsolationTest
from tests.security.test_filesystem_security import FilesystemSecurityTest
from tests.security.test_process_isolation import ProcessIsolationTest
from tests.security.test_resource_isolation import ResourceIsolationTest


class TestRunner:
    """Unified test runner for E2B sandbox tests"""
    
    def __init__(self, template: str, concurrency: int = 50, output_dir: str = "reports"):
        self.template = template
        self.concurrency = concurrency
        self.output_dir = output_dir
        self.report = ReportGenerator(output_dir=output_dir)
        
        self.report.set_metadata({
            "Template ID": template,
            "Concurrency": concurrency,
            "Test Time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
    
    def run_performance_tests(self):
        """Run all performance tests"""
        print(f"\n{'#'*60}")
        print(f"# PERFORMANCE TESTS")
        print(f"{'#'*60}\n")
        
        # Cold Start Test
        print(f"\n--- Cold Start Test ---")
        cold_start = ColdStartTest(template=self.template, report=self.report)
        cold_start.run_sequential_test(runs=5)
        cold_start.run_concurrent_test(count=10, concurrency=self.concurrency)
        
        # Throughput Test
        print(f"\n--- Throughput Test ---")
        throughput = ThroughputTest(template=self.template, concurrency=self.concurrency, report=self.report)
        throughput.test_concurrent_creation(count=min(self.concurrency, 20))
        
        # Command Latency Test
        print(f"\n--- Command Latency Test ---")
        latency = CommandLatencyTest(template=self.template, report=self.report)
        latency.run_all_tests(iterations=50)
        
        # Resource Monitor Test
        print(f"\n--- Resource Monitor Test ---")
        monitor = ResourceMonitorTest(template=self.template, report=self.report)
        monitor.monitor_idle_sandbox(duration=30, interval=5)
    
    def run_security_tests(self):
        """Run all security tests"""
        print(f"\n{'#'*60}")
        print(f"# SECURITY TESTS")
        print(f"{'#'*60}\n")
        
        # Network Isolation Test
        print(f"\n--- Network Isolation Test ---")
        network = NetworkIsolationTest(template=self.template, report=self.report)
        network.test_external_http_access()
        
        # Filesystem Security Test
        print(f"\n--- Filesystem Security Test ---")
        filesystem = FilesystemSecurityTest(template=self.template, report=self.report)
        filesystem.test_file_isolation()
        
        # Process Isolation Test
        print(f"\n--- Process Isolation Test ---")
        process = ProcessIsolationTest(template=self.template, report=self.report)
        process.test_process_visibility()
        
        # Resource Isolation Test
        print(f"\n--- Resource Isolation Test ---")
        resource = ResourceIsolationTest(template=self.template, report=self.report)
        resource.run_all_tests()
    
    def run_all_tests(self):
        """Run all tests"""
        overall_start = time.time()
        
        self.run_performance_tests()
        self.run_security_tests()
        
        total_time = time.time() - overall_start
        print(f"\n{'='*60}")
        print(f"  All tests completed in {total_time:.2f}s")
        print(f"{'='*60}\n")
    
    def generate_report(self, filename: str = None) -> str:
        """Generate final report"""
        if not filename:
            filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        return self.report.save(filename)


def main():
    parser = argparse.ArgumentParser(description="E2B Sandbox Test Runner")
    
    # Test selection
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--performance', action='store_true', help='Run performance tests')
    parser.add_argument('--security', action='store_true', help='Run security tests')
    parser.add_argument('--test', type=str, help='Run specific test')
    
    # Configuration
    parser.add_argument('--template', type=str, help='Sandbox template ID')
    parser.add_argument('--concurrency', type=int, default=50, help='Concurrency level (default: 50)')
    parser.add_argument('--output', type=str, help='Output report filename')
    parser.add_argument('--output-dir', type=str, default='reports', help='Output directory')
    
    args = parser.parse_args()
    
    # Validate template
    template = args.template or os.environ.get("CUBE_TEMPLATE_ID")
    if not template:
        print("Error: Template ID required. Set CUBE_TEMPLATE_ID or use --template")
        sys.exit(1)
    
    # Validate API key
    if not os.environ.get("E2B_API_KEY"):
        print("Warning: E2B_API_KEY not set")
    
    # Create runner
    runner = TestRunner(
        template=template,
        concurrency=args.concurrency,
        output_dir=args.output_dir
    )
    
    # Determine what to run
    if not (args.all or args.performance or args.security or args.test):
        parser.print_help()
        sys.exit(1)
    
    # Run tests
    if args.all:
        runner.run_all_tests()
    elif args.performance:
        runner.run_performance_tests()
    elif args.security:
        runner.run_security_tests()
    elif args.test:
        # Run specific test
        test_name = args.test.lower()
        if 'cold' in test_name or 'start' in test_name:
            test = ColdStartTest(template=template, report=runner.report)
            test.run_sequential_test(runs=5)
            test.run_concurrent_test(count=args.concurrency, concurrency=min(args.concurrency, 10))
        elif 'throughput' in test_name:
            test = ThroughputTest(template=template, concurrency=args.concurrency, report=runner.report)
            test.test_concurrent_creation(count=args.concurrency)
        elif 'latency' in test_name or 'cmd' in test_name:
            test = CommandLatencyTest(template=template, report=runner.report)
            test.run_all_tests()
        elif 'monitor' in test_name or 'resource' in test_name:
            test = ResourceMonitorTest(template=template, report=runner.report)
            test.monitor_idle_sandbox()
        elif 'network' in test_name:
            test = NetworkIsolationTest(template=template, report=runner.report)
            test.test_external_http_access()
        elif 'filesystem' in test_name or 'file' in test_name:
            test = FilesystemSecurityTest(template=template, report=runner.report)
            test.test_file_isolation()
        elif 'process' in test_name:
            test = ProcessIsolationTest(template=template, report=runner.report)
            test.test_process_visibility()
        elif 'isolation' in test_name:
            test = ResourceIsolationTest(template=template, report=runner.report)
            test.run_all_tests()
        else:
            print(f"Unknown test: {args.test}")
            print("Available tests: cold_start, throughput, latency, monitor, network, filesystem, process, isolation")
            sys.exit(1)
    
    # Generate report
    report_path = runner.generate_report(args.output)
    
    print(f"\n{'='*60}")
    print(f"  Test report saved to: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()