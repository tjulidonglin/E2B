# huawei_osinfo.py — E2B Sandbox OS 与内存信息采集脚本
# 测试流程：创建沙箱 → 采集 OS/内存信息 → 保持 30s 存活 → kill 清理

import os
import sys
import time
import httpx

# ============================================================
# 环境配置：绕过华为企业代理
# ============================================================
os.environ["NO_PROXY"] = "huaweicloud-agentnetwork.com,huaweicloud.com,agentsphere.cn-south-1.myhuaweicloud.com,default-sandbox-gateway-mu2tkmdfhe.agentgateway.cn-south-1.huaweicloud-agentnetwork.com"
os.environ["no_proxy"] = os.environ["NO_PROXY"]

from e2b_code_interpreter import Sandbox
from e2b.api.client_sync import get_transport
from e2b.envd.client_sync import create_rpc_client
from e2b.envd.process import process_connect
from e2b.envd.filesystem import filesystem_connect

# ============================================================
# 配置：优先使用环境变量，回退到默认值
# ============================================================
E2B_API_KEY = os.environ.get("E2B_API_KEY", "")
E2B_API_URL = os.environ.get("E2B_API_URL", "https://agentsphere.cn-south-1.myhuaweicloud.com")
E2B_SANDBOX_URL = os.environ.get("E2B_SANDBOX_URL", "https://default-sandbox-gateway-mu2tkmdfhe.agentgateway.cn-south-1.huaweicloud-agentnetwork.com")
TEMPLATE = os.environ.get("CUBE_TEMPLATE_ID", "20f1421a-f0e3-4b4c-878b-af029b03cc77")

KEEPALIVE_SEC = 30  # 沙箱保持存活时间（秒）

MAX_RETRIES = 10
WAIT_SEC = 3
RETRYABLE = ["connection refused", "524", "unauthorized", "401"]


# ============================================================
# 核心补丁函数（同 huawei.py，详见 huawei.py 注释）
# ============================================================
def patch_sandbox_redirects(sbx):
    @property
    def _client_with_redirects(self):
        return httpx.Client(
            transport=get_transport(self.connection_config, http2=False),
            follow_redirects=True,
        )
    type(sbx)._client = _client_with_redirects

    new_envd_api = httpx.Client(
        base_url=sbx.envd_api_url,
        transport=get_transport(sbx.connection_config),
        headers=sbx.connection_config.sandbox_headers,
        follow_redirects=True,
    )
    new_envd_streaming = httpx.Client(
        base_url=sbx.envd_api_url,
        transport=get_transport(sbx.connection_config, for_streaming=True),
        headers=sbx.connection_config.sandbox_headers,
        follow_redirects=True,
    )
    old = sbx._envd_api
    sbx._envd_api = new_envd_api
    if hasattr(sbx, "_filesystem"):
        sbx._filesystem._envd_api = new_envd_api
        sbx._filesystem._envd_api_streaming = new_envd_streaming
        sbx._filesystem._rpc = create_rpc_client(
            filesystem_connect.FilesystemClientSync,
            sbx.envd_api_url,
            sbx.connection_config,
        )
    if hasattr(sbx, "_commands"):
        sbx._commands._envd_api = new_envd_api
        sbx._commands._rpc = create_rpc_client(
            process_connect.ProcessClientSync,
            sbx.envd_api_url,
            sbx.connection_config,
        )
    if hasattr(sbx, "_pty"):
        sbx._pty._envd_api = new_envd_api
    old.close()


def is_retryable(e):
    """判断异常是否可重试（沙箱启动初期的短暂不可用）"""
    return any(k in str(e).lower() for k in RETRYABLE)


def retry(fn, name, *args, **kwargs):
    """带重试的函数调用：对可重试异常自动重试，不可重试异常直接抛出。"""
    last_exc = None
    for i in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if is_retryable(e):
                print(f"  sandbox 重试 {i}/{MAX_RETRIES}: {e}")
                time.sleep(WAIT_SEC)
                continue
            raise
    print(f"  {name} 超时, 最后异常: {last_exc}", file=sys.stderr)
    sys.exit(1)


def run_cmd(sbx, cmd, timeout=15):
    """在沙箱中执行 shell 命令并返回 stdout 文本"""
    r = retry(sbx.commands.run, "commands.run", cmd, timeout=timeout)
    return r.stdout


def main():
    # 检查 API Key 是否已设置
    if not E2B_API_KEY:
        print("Error: E2B_API_KEY 环境变量未设置", file=sys.stderr)
        sys.exit(1)

    # --- Step 0: 打印配置信息 ---
    print("=" * 60)
    print("E2B Sandbox OS 信息采集脚本")
    print("=" * 60)
    print(f"API URL:     {E2B_API_URL}")
    print(f"Sandbox URL: {E2B_SANDBOX_URL}")
    print(f"Template ID: {TEMPLATE}")
    print(f"API Key:     {E2B_API_KEY[:10]}...{E2B_API_KEY[-6:]}")
    print("=" * 60)
    
    # --- Step 1: 创建 Sandbox ---
    print("\n开始创建 Sandbox...")
    try:
        sbx = Sandbox.create(
            template=TEMPLATE, api_key=E2B_API_KEY,
            api_url=E2B_API_URL, sandbox_url=E2B_SANDBOX_URL, timeout=60,
        )
    except Exception as e:
        error_msg = str(e)
        print(f"\n创建失败: {error_msg}", file=sys.stderr)
        
        # 提供详细的错误诊断
        if "403" in error_msg or "statusCode=403" in error_msg:
            print("\n" + "=" * 60, file=sys.stderr)
            print("错误诊断: 403 权限错误", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print("可能的原因:", file=sys.stderr)
            print("  1. API Key 已过期或无效", file=sys.stderr)
            print("  2. Template ID 不存在或无权访问", file=sys.stderr)
            print("  3. 华为云服务端权限配置问题", file=sys.stderr)
            print("\n建议解决方案:", file=sys.stderr)
            print("  1. 检查 E2B_API_KEY 环境变量是否正确", file=sys.stderr)
            print("  2. 检查 CUBE_TEMPLATE_ID 环境变量是否正确", file=sys.stderr)
            print("  3. 联系华为云服务提供方确认服务状态", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
        elif "500" in error_msg:
            print("\n" + "=" * 60, file=sys.stderr)
            print("错误诊断: 500 服务端错误", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            print("可能的原因:", file=sys.stderr)
            print("  1. 华为云服务端暂时不可用", file=sys.stderr)
            print("  2. 服务端配置问题", file=sys.stderr)
            print("\n建议解决方案:", file=sys.stderr)
            print("  1. 稍后重试", file=sys.stderr)
            print("  2. 联系华为云服务提供方", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
        
        sys.exit(1)

    print(f"Sandbox 创建成功, sandbox_id={sbx.sandbox_id}")
    print(f"traffic_access_token: {sbx.traffic_access_token}")
    sbx.connection_config._ConnectionConfig__extra_sandbox_headers[
        "E2b-Traffic-Access-Token"
    ] = sbx.traffic_access_token
    patch_sandbox_redirects(sbx)

    try:
        # --- Step 2: 等待就绪 ---
        print("\n0. 等待 Sandbox 就绪:")
        t0 = time.time()
        retry(sbx.run_code, "run_code", "print('ready')", timeout=15)

        print(f"   Sandbox 已就绪, 用时 {time.time() - t0:.1f}s")

        # --- Step 3: 采集 OS 信息 ---
        print("\n1. OS 信息:")
        os_info = run_cmd(sbx, "uname -a")
        print(f"   {os_info}")

        # --- Step 4: 采集内存信息 ---
        print("\n2. 内存信息 (free -h):")
        mem_info = run_cmd(sbx, "free -h")
        print(mem_info)

        print("\n3. 内存详情 (/proc/meminfo):")
        proc_mem = run_cmd(sbx, "head -10 /proc/meminfo")
        print(proc_mem)

        # --- Step 5: 采集 CPU 信息 ---
        print("4. CPU 信息:")
        cpu_info = run_cmd(sbx, "lscpu | head -15")
        print(cpu_info)

        # --- Step 6: 采集磁盘信息 ---
        print("5. 磁盘信息 (df -h):")
        disk_info = run_cmd(sbx, "df -h")
        print(disk_info)

        # --- Step 7: 保持沙箱存活 ---
        print(f"\n6. 沙箱保持存活 {KEEPALIVE_SEC}s...")
        for i in range(KEEPALIVE_SEC, 0, -1):
            print(f"   剩余 {i:2d}s  (sandbox_id={sbx.sandbox_id[:12]}...)", end="\r")
            time.sleep(1)
        print(f"   存活结束{' ' * 40}")

    except Exception as e:
        print(f"\n操作失败: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # --- Step 8: 清理 Sandbox ---
        print("\n清理 Sandbox...")
        try:
            sbx.kill()
            print("Sandbox 已清理")
        except Exception as e:
            print(f"清理失败: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()