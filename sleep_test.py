import argparse
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from e2b_code_interpreter import Sandbox


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="创建沙箱，在沙箱内执行 sleep 后关闭")
    parser.add_argument(
        "--seconds",
        type=float,
        default=10,
        help="sleep 时长（秒），默认 10",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="并发启动的沙箱数量，默认 1",
    )
    return parser.parse_args()


def run_single(sandbox_id: int, seconds: float, template: str):
    sleep_command = f"sleep {seconds}"
    overall_start = time.perf_counter()

    sandbox = Sandbox.create(template=template)
    create_elapsed = time.perf_counter() - overall_start
    print(f"[沙箱 {sandbox_id}] 创建完成，耗时 {create_elapsed:.3f}s")

    try:
        cmd_start = time.perf_counter()
        result = sandbox.commands.run(sleep_command)
        cmd_elapsed = time.perf_counter() - cmd_start
        print(
            f"[沙箱 {sandbox_id}] 命令执行完成，exit_code={result.exit_code}，耗时 {cmd_elapsed:.3f}s"
        )
        if result.stderr:
            print(f"[沙箱 {sandbox_id}] stderr: {result.stderr.strip()}")
    finally:
        sandbox.kill()

    total_elapsed = time.perf_counter() - overall_start
    print(f"[沙箱 {sandbox_id}] 已关闭，总耗时 {total_elapsed:.3f}s")
    return create_elapsed, cmd_elapsed, total_elapsed


def main():
    args = parse_args()
    if args.count < 1:
        print("错误: --count 必须大于等于 1。")
        return 1

    template = os.environ.get("CUBE_TEMPLATE_ID")
    if not template:
        print("错误: 未检测到 CUBE_TEMPLATE_ID 环境变量。")
        print("请设置 Template ID，例如:")
        print("  export CUBE_TEMPLATE_ID=your_template_id")
        return 1

    if not os.environ.get("E2B_API_KEY"):
        print("警告: 未检测到 E2B_API_KEY 环境变量。")

    print(
        f"并发启动 {args.count} 个沙箱 (template={template}, sleep={args.seconds}s)..."
    )
    overall_start = time.perf_counter()

    creates = []
    commands = []
    totals = []
    with ThreadPoolExecutor(max_workers=args.count) as executor:
        futures = {
            executor.submit(run_single, i, args.seconds, template): i
            for i in range(1, args.count + 1)
        }
        for future in as_completed(futures):
            create_elapsed, cmd_elapsed, total_elapsed = future.result()
            creates.append(create_elapsed)
            commands.append(cmd_elapsed)
            totals.append(total_elapsed)

    overall_elapsed = time.perf_counter() - overall_start
    print(f"\n全部 {args.count} 个沙箱执行完成。")
    print(f"创建平均耗时: {sum(creates) / len(creates):.3f}s")
    print(f"命令平均耗时: {sum(commands) / len(commands):.3f}s")
    print(f"单个沙箱平均总耗时: {sum(totals) / len(totals):.3f}s")
    print(f"整体总耗时: {overall_elapsed:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())