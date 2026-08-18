#!/usr/bin/env python3
"""
E2B Sandbox Cold Start Time Test Script

This script tests the cold start time of E2B sandboxes, measuring the time
from API call to create a sandbox until a simple "echo 0" command completes.

Usage:
    python cold_start_test.py [--count N] [--api-key KEY]
"""

import argparse
import os
import sys
import time
from typing import List, Optional

try:
    from e2b import Sandbox
except ImportError:
    print("Error: e2b package not installed. Please install it with: pip install e2b")
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test E2B sandbox cold start time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python cold_start_test.py                    # Run 10 tests (default)
    python cold_start_test.py --count 20         # Run 20 tests
    python cold_start_test.py --api-key your_key # Specify API key
        """
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of test iterations (default: 10)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="E2B API key (overrides E2B_API_KEY environment variable)"
    )
    return parser.parse_args()


def get_api_key(cli_key: Optional[str]) -> str:
    """Get API key from CLI argument or environment variable."""
    if cli_key:
        return cli_key
    
    env_key = os.environ.get("E2B_API_KEY")
    if env_key:
        return env_key
    
    print("Error: E2B API key not provided.")
    print("Please either:")
    print("  1. Pass it via --api-key argument")
    print("  2. Set E2B_API_KEY environment variable")
    sys.exit(1)


def run_single_test(api_key: str, test_num: int, total: int) -> float:
    """
    Run a single cold start test.
    
    Returns:
        float: Time in seconds from sandbox creation to command completion
    """
    print(f"\n[{test_num}/{total}] Starting test...")
    
    start_time = time.time()
    
    try:
        # Create sandbox and execute simple command
        sandbox = Sandbox(api_key=api_key)
        result = sandbox.run_code("echo 0")
        elapsed_time = time.time() - start_time
        
        # Clean up
        sandbox.close()
        
        print(f"[{test_num}/{total}] Completed in {elapsed_time:.3f}s")
        return elapsed_time
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"[{test_num}/{total}] Failed after {elapsed_time:.3f}s: {e}")
        raise


def calculate_percentile(sorted_times: List[float], percentile: float) -> float:
    """
    Calculate the given percentile of a sorted list of times.
    
    Args:
        sorted_times: List of times sorted in ascending order
        percentile: Percentile to calculate (e.g., 95 for P95)
    
    Returns:
        float: The percentile value
    """
    if not sorted_times:
        return 0.0
    
    n = len(sorted_times)
    index = (percentile / 100) * (n - 1)
    lower_idx = int(index)
    upper_idx = min(lower_idx + 1, n - 1)
    
    # Linear interpolation
    fraction = index - lower_idx
    return sorted_times[lower_idx] * (1 - fraction) + sorted_times[upper_idx] * fraction


def calculate_statistics(times: List[float]) -> dict:
    """Calculate statistics from test times."""
    if not times:
        return {
            "count": 0,
            "mean": 0,
            "min": 0,
            "max": 0,
            "p95": 0,
            "p99": 0
        }
    
    sorted_times = sorted(times)
    n = len(times)
    
    return {
        "count": n,
        "mean": sum(times) / n,
        "min": sorted_times[0],
        "max": sorted_times[-1],
        "p95": calculate_percentile(sorted_times, 95),
        "p99": calculate_percentile(sorted_times, 99)
    }


def print_results(times: List[float], stats: dict) -> None:
    """Print detailed test results and statistics."""
    print("\n" + "=" * 60)
    print("E2B Sandbox Cold Start Time Test Results")
    print("=" * 60)
    
    # Print individual test times
    print("\nIndividual Test Times:")
    print("-" * 40)
    for i, t in enumerate(times, 1):
        print(f"  Test {i:3d}: {t:.3f}s")
    
    # Print statistics
    print("\n" + "-" * 40)
    print("Statistics:")
    print("-" * 40)
    print(f"  Test Count:  {stats['count']}")
    print(f"  Mean:        {stats['mean']:.3f}s")
    print(f"  Min:         {stats['min']:.3f}s")
    print(f"  Max:         {stats['max']:.3f}s")
    print(f"  P95:         {stats['p95']:.3f}s")
    print(f"  P99:         {stats['p99']:.3f}s")
    print("=" * 60)


def main():
    """Main entry point."""
    args = parse_args()
    api_key = get_api_key(args.api_key)
    
    print("=" * 60)
    print("E2B Sandbox Cold Start Time Test")
    print("=" * 60)
    print(f"Number of tests: {args.count}")
    print(f"Test command: echo 0")
    print("=" * 60)
    
    times: List[float] = []
    failed = 0
    
    for i in range(1, args.count + 1):
        try:
            elapsed = run_single_test(api_key, i, args.count)
            times.append(elapsed)
        except Exception:
            failed += 1
    
    if not times:
        print("\nError: All tests failed!")
        sys.exit(1)
    
    # Calculate and print results
    stats = calculate_statistics(times)
    print_results(times, stats)
    
    if failed > 0:
        print(f"\nWarning: {failed} test(s) failed and were excluded from statistics")


if __name__ == "__main__":
    main()