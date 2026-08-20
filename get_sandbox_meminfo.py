import os
from e2b_code_interpreter import Sandbox  # 直接使用 E2B SDK！

# CubeSandbox 在底层无缝接管了所有的请求
with Sandbox.create(template=os.environ["CUBE_TEMPLATE_ID"]) as sandbox:
	result = sandbox.commands.run("cat /proc/meminfo")

if result.exit_code == 0:
    meminfo = {}
    for line in result.stdout.strip().split("\n"):
        parts = line.split(":")
        if len(parts) == 2:
            key = parts[0].strip()
            value = int(parts[1].strip().split()[0])  # 单位 kB
            meminfo[key] = value

    total_kb = meminfo["MemTotal"]
    available_kb = meminfo["MemAvailable"]
    used_kb = total_kb - available_kb

    print(f"总内存:   {total_kb / 1024:.1f} MB")
    print(f"已用内存: {used_kb / 1024:.1f} MB")
    print(f"可用内存: {available_kb / 1024:.1f} MB")
else:
    print(f"读取失败: {result.stderr}")
    print(result)