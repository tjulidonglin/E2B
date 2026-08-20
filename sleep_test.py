import argparse
import os
import time

from e2b_code_interpreter import Sandbox


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="创建沙箱，在沙箱内执行 sleep 后关闭")
    parser.add_argument(
        "--seconds",
        type=float,
        default=10,
        help="sleep 时长（秒），默认 10",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    sleep_command = f"sleep {args.seconds}"

    template = os.environ.get("CUBE_TEMPLATE_ID")
    if not template:
        print("错误: 未检测到 CUBE_TEMPLATE_ID 环境变量。")
        print("请设置 Template ID，例如:")
        print("  export CUBE_TEMPLATE_ID=your_template_id")
        return 1

    if not os.environ.get("E2B_API_KEY"):
        print("警告: 未检测到 E2B_API_KEY 环境变量。")

    print(f"正在创建沙箱 (template={template})...")
    overall_start = time.perf_counter()

    sandbox = Sandbox.create(template=template)
    create_elapsed = time.perf_counter() - overall_start
    print(f"沙箱创建完成，耗时 {create_elapsed:.3f}s")

    try:
        print(f"在沙箱内执行命令: {sleep_command}")
        cmd_start = time.perf_counter()
        result = sandbox.commands.run(sleep_command)
        cmd_elapsed = time.perf_counter() - cmd_start
        print(f"命令执行完成，exit_code={result.exit_code}，耗时 {cmd_elapsed:.3f}s")
        if result.stderr:
            print(f"stderr: {result.stderr.strip()}")
    finally:
        print("关闭沙箱...")
        sandbox.kill()

    total_elapsed = time.perf_counter() - overall_start
    print(f"沙箱已关闭，总耗时 {total_elapsed:.3f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())