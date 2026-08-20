"""
E2B Sandbox 冷启动时间测试脚本

测试逻辑：
1. 多次创建全新 Sandbox，记录从发起创建到 Sandbox 就绪的耗时
2. Sandbox 创建后，通过执行极简命令（echo 1）探测沙箱内部是否真正 ready
3. 若命令执行失败则短暂等待后重试，直到成功或超时
4. 每次创建后立即销毁，确保下一次是真正的冷启动
5. 统计最大/最小/平均/中位数等指标，区分「创建耗时」和「内部就绪耗时」
"""

import os
import time
import statistics
from datetime import datetime

from e2b_code_interpreter import Sandbox  # 直接使用 E2B SDK！


PROBE_CMD = "echo 1"
PROBE_RETRY_INTERVAL = 0.02  # 每次重试间隔（秒）
PROBE_TIMEOUT = 30            # 探测超时阈值（秒）


def probe_sandbox_ready(sbx) -> tuple[bool, float]:
    """
    通过执行极简命令探测沙箱内部是否真正 ready。
    返回 (是否成功, 探测耗时秒数)。
    """
    probe_start = time.perf_counter()
    while True:
        try:
            result = sbx.commands.run(PROBE_CMD, timeout=5)
            if result.exit_code == 0:
                return True, time.perf_counter() - probe_start
        except Exception:
            pass

        if time.perf_counter() - probe_start > PROBE_TIMEOUT:
            return False, time.perf_counter() - probe_start

        time.sleep(PROBE_RETRY_INTERVAL)


def measure_cold_start_once() -> tuple[float, float, float]:
    """
    测量单次冷启动耗时。
    返回 (创建耗时, 探测耗时, 总耗时)，失败时对应值为 -1.0。
    """
    start = time.perf_counter()
    try:
        sbx = Sandbox.create(template=os.environ["CUBE_TEMPLATE_ID"])
    except Exception as e:
        print(f"  创建 Sandbox 失败: {e}")
        return -1.0, -1.0, -1.0

    create_elapsed = time.perf_counter() - start

    # 探测沙箱内部是否真正 ready
    ok, probe_elapsed = probe_sandbox_ready(sbx)
    total_elapsed = create_elapsed + probe_elapsed

    if not ok:
        print(f"  探测超时（{PROBE_TIMEOUT}s），沙箱内部未就绪")
        try:
            sbx.kill()
        except Exception:
            pass
        return create_elapsed, -1.0, -1.0

    # 立即销毁，确保下一次测试是冷启动而非热启动
    try:
        sbx.kill()
    except Exception as e:
        print(f"  销毁 Sandbox 时警告: {e}")

    return create_elapsed, probe_elapsed, total_elapsed


def run_cold_start_test(runs: int = 10) -> list[tuple[float, float, float]]:
    """执行多次冷启动测试，返回 [(创建耗时, 探测耗时, 总耗时), ...]"""
    print(f"\n{'=' * 60}")
    print(f"  E2B Sandbox 冷启动时间测试")
    print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  测试次数: {runs}")
    print(f"  探测命令: {PROBE_CMD}")
    print(f"  探测超时: {PROBE_TIMEOUT}s")
    print(f"{'=' * 60}\n")

    results = []

    for i in range(runs):
        print(f"[{i + 1}/{runs}] 正在创建 Sandbox（冷启动）...", end="", flush=True)
        create_t, probe_t, total_t = measure_cold_start_once()

        if total_t < 0:
            print(f" 失败 (创建={create_t:.3f}s, 探测=失败)")
            continue

        results.append((create_t, probe_t, total_t))
        print(f" 完成 | 创建={create_t:.3f}s 探测={probe_t:.3f}s 总计={total_t:.3f}s")

        # 测试间隔，避免触发限流
        if i < runs - 1:
            time.sleep(1)

    return results


def print_statistics(results: list[tuple[float, float, float]]):
    """打印统计信息"""
    if not results:
        print("\n无有效测试结果。")
        return

    create_times = [r[0] for r in results]
    probe_times = [r[1] for r in results]
    total_times = [r[2] for r in results]

    print(f"\n{'=' * 60}")
    print(f"  测试结果统计")
    print(f"{'=' * 60}")
    print(f"  有效测试次数: {len(results)}")

    for label, times in [("创建耗时", create_times), ("探测耗时", probe_times), ("总冷启动", total_times)]:
        print(f"\n  ── {label} ──")
        print(f"    最小值: {min(times):.3f}s")
        print(f"    最大值: {max(times):.3f}s")
        print(f"    平均值: {statistics.mean(times):.3f}s")
        if len(times) >= 2:
            print(f"    中位数: {statistics.median(times):.3f}s")
            print(f"    标准差: {statistics.stdev(times):.3f}s")
            p95_index = int(len(times) * 0.95)
            sorted_times = sorted(times)
            p95 = sorted_times[min(p95_index, len(times) - 1)]
            print(f"    P95:    {p95:.3f}s")

    print(f"\n{'=' * 60}")
    print(f"  逐次结果:")
    print(f"  {'#':>4}  {'创建':>8}  {'探测':>8}  {'总计':>8}  耗时分布")
    print(f"  {'─' * 4}  {'─' * 8}  {'─' * 8}  {'─' * 8}  {'─' * 40}")
    for i, (c, p, t) in enumerate(results, 1):
        bar_len = int(t * 20)
        bar = "█" * bar_len + "░" * (40 - bar_len) if bar_len < 40 else "█" * 40
        print(f"  #{i:02d}  {c:7.3f}s  {p:7.3f}s  {t:7.3f}s  |{bar}|")
    print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="E2B Sandbox 冷启动时间测试")
    parser.add_argument(
        "-n", "--runs", type=int, default=10, help="测试次数（默认 10）"
    )
    args = parser.parse_args()

    # 检查 API Key 是否配置
    if not os.environ.get("E2B_API_KEY"):
        print("警告: 未检测到 E2B_API_KEY 环境变量。")
        print("请通过以下方式设置:")
        print("  export E2B_API_KEY=your_api_key  (Linux/Mac)")
        print("  set E2B_API_KEY=your_api_key     (Windows)")
        print("或从 https://e2b.dev/dashboard 获取 API Key\n")

    # 检查 Template ID 是否配置
    if not os.environ.get("CUBE_TEMPLATE_ID"):
        print("警告: 未检测到 CUBE_TEMPLATE_ID 环境变量。")
        print("请设置自定义模板 ID 或使用默认模板。")
        print("  set CUBE_TEMPLATE_ID=your_template_id\n")

    results = run_cold_start_test(args.runs)
    print_statistics(results)


if __name__ == "__main__":
    main()