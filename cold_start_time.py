import time
import os
import statistics
from datetime import datetime

from e2b_code_interpreter import Sandbox  # 直接使用 E2B SDK！


def measure_cold_start_once() -> float:
    """测量单次冷启动耗时（秒）"""
    start = time.perf_counter()
    try:
        sbx = Sandbox.create(template=os.environ["CUBE_TEMPLATE_ID"])
    except Exception as e:
        print(f"  创建 Sandbox 失败: {e}")
        return -1.0

    # Sandbox 创建即意味着冷启动完成（SDK 在构造函数中等待就绪）
    elapsed = time.perf_counter() - start

    # 立即销毁，确保下一次测试是冷启动而非热启动
    try:
        sbx.kill()
    except Exception as e:
        print(f"  销毁 Sandbox 时警告: {e}")

    return elapsed


def run_cold_start_test(runs: int = 10) -> list[float]:
    """执行多次冷启动测试"""
    print(f"\n{'=' * 60}")
    print(f"  E2B Sandbox 冷启动时间测试")
    print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  测试次数: {runs}")
    print(f"{'=' * 60}\n")

    results = []

    for i in range(runs):
        print(f"[{i + 1}/{runs}] 正在创建 Sandbox（冷启动）...", end="", flush=True)
        elapsed = measure_cold_start_once()

        if elapsed < 0:
            print(" 失败，跳过")
            continue

        results.append(elapsed)
        print(f" 完成，耗时 {elapsed:.3f}s")

        # 测试间隔，避免触发限流
        if i < runs - 1:
            time.sleep(1)

    return results


def print_statistics(results: list[float]):
    """打印统计信息"""
    if not results:
        print("\n无有效测试结果。")
        return

    print(f"\n{'=' * 60}")
    print(f"  测试结果统计")
    print(f"{'=' * 60}")
    print(f"  有效测试次数: {len(results)}")
    print(f"  最小冷启动时间: {min(results):.3f}s")
    print(f"  最大冷启动时间: {max(results):.3f}s")
    print(f"  平均冷启动时间: {statistics.mean(results):.3f}s")
    if len(results) >= 2:
        print(f"  中位数:         {statistics.median(results):.3f}s")
        print(f"  标准差:         {statistics.stdev(results):.3f}s")
        p95_index = int(len(results) * 0.95)
        sorted_results = sorted(results)
        p95 = sorted_results[min(p95_index, len(results) - 1)]
        print(f"  P95:            {p95:.3f}s")
    print(f"{'=' * 60}\n")

    print("  逐次结果:")
    for i, r in enumerate(results, 1):
        bar_len = int(r * 20)
        bar = "█" * bar_len + "░" * (40 - bar_len) if bar_len < 40 else "█" * 40
        print(f"    #{i:02d} {r:6.3f}s |{bar}|")
    print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="E2B Sandbox 冷启动时间测试")
    parser.add_argument(
        "-n", "--runs", type=int, default=10, help="测试次数（默认 10）"
    )
    args = parser.parse_args()

    # 检查 API Key 是否配置
    import os

    if not os.environ.get("E2B_API_KEY"):
        print("警告: 未检测到 E2B_API_KEY 环境变量。")
        print("请通过以下方式设置:")
        print("  export E2B_API_KEY=your_api_key  (Linux/Mac)")
        print("  set E2B_API_KEY=your_api_key     (Windows)")
        print("或从 https://e2b.dev/dashboard 获取 API Key\n")

    results = run_cold_start_test(args.runs)
    print_statistics(results)


if __name__ == "__main__":
    main()