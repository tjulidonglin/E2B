# -*- coding: utf-8 -*-
"""
Cube Sandbox 测试脚本（本地自托管 Cube Sandbox）

测试内容：
- 沙箱创建
- 代码执行
- 系统信息
- 资源清理

支持并发启动性能测试：
- -c / --concurrency N  并发启动 N 个沙箱（默认 1，即单沙箱基础测试）

环境变量：
- E2B_API_URL:      Cube API Server 地址（默认端口 3000），如 http://10.211.55.7:3000
- E2B_API_KEY:      API 密钥，本地部署通常为占位值（默认 e2b_000000）
- CUBE_TEMPLATE_ID: 沙箱模板 ID

说明：
自托管 Cube Sandbox 的沙箱数据面（envd / Jupyter）通过 CubeProxy 暴露。
本脚本自动启用 CubeProxy 的路径模式 /sandbox/<沙箱ID>/<端口>/，
无需通配符 DNS 解析，适合内网/单机环境直接访问。
"""
import argparse
import html
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from e2b_code_interpreter import Sandbox

import e2b.connection_config as cc
import e2b_code_interpreter.code_interpreter_sync as cis

E2B_API_URL = os.environ.get("E2B_API_URL")
E2B_API_KEY = os.environ.get("E2B_API_KEY", "e2b_000000")
CUBE_TEMPLATE_ID = os.environ.get("CUBE_TEMPLATE_ID")

# 每个沙箱执行的测试代码
TEST_CODE = "print('Hello from Cube Sandbox, safely isolated!')"

# 系统信息探测代码
SYSTEM_INFO_CODE = """
import platform
print(f"Python: {platform.python_version()}")
print(f"Hostname: {platform.node()}")
print(f"OS: {platform.platform()}")
"""


def _patch_for_cube_proxy(proxy_host):
    """将 E2B SDK 数据面请求切换为 CubeProxy 路径模式。

    自托管 Cube Sandbox 的沙箱数据面（envd / Jupyter）通过 CubeProxy 暴露。
    本函数将 SDK 的数据面 URL 改为路径模式 /sandbox/<沙箱ID>/<端口>/，
    从而无需通配符 DNS 解析即可在内网/单机环境访问沙箱。
    """
    def _get_sandbox_url(self, sandbox_id, sandbox_domain):
        return f"http://{proxy_host}/sandbox/{sandbox_id}/{self.envd_port}"

    def _get_sandbox_direct_url(self, sandbox_id, sandbox_domain):
        return f"http://{proxy_host}/sandbox/{sandbox_id}/{self.envd_port}"

    def _get_host(self, sandbox_id, sandbox_domain, port):
        return f"{proxy_host}/sandbox/{sandbox_id}/{port}"

    def _jupyter_url(self):
        return f"http://{proxy_host}/sandbox/{self.sandbox_id}/{cis.JUPYTER_PORT}"

    cc.ConnectionConfig.get_sandbox_url = _get_sandbox_url
    cc.ConnectionConfig.get_sandbox_direct_url = _get_sandbox_direct_url
    cc.ConnectionConfig.get_host = _get_host
    cis.Sandbox._jupyter_url = property(_jupyter_url)


def _resolve_config(args):
    """根据命令行参数与环境变量解析最终配置，并应用 CubeProxy 补丁。"""
    api_url = args.api_url or E2B_API_URL
    api_key = args.api_key or E2B_API_KEY
    template = args.template or CUBE_TEMPLATE_ID

    if not api_url:
        print("Error: 未设置 E2B_API_URL（Cube API Server 地址，如 http://10.211.55.7:3000）")
        sys.exit(1)
    if not template:
        print("Error: 未设置 CUBE_TEMPLATE_ID（沙箱模板 ID）")
        sys.exit(1)

    # CubeProxy 与 Cube API Server 同机部署，复用 API 地址中的主机名
    proxy_host = urlparse(api_url).hostname
    _patch_for_cube_proxy(proxy_host)

    return api_url, api_key, template


def _extract_stdout(result):
    """从 run_code 结果中提取 stdout 文本。"""
    try:
        stdout = getattr(getattr(result, "logs", None), "stdout", None)
        if stdout:
            if isinstance(stdout, list):
                return "".join(stdout).strip()
            return str(stdout).strip()
    except Exception:
        pass
    return "N/A"


def _is_retriable_error(exc):
    """判断异常是否值得重试（408 超时、429 限流、5xx 服务端错误、连接错误）。"""
    msg = str(exc)
    for code in ("408", "429", "500", "502", "503", "504"):
        if msg.startswith(code):
            return True
    return any(k in type(exc).__name__ for k in ("Connect", "Timeout"))


def _create_with_retry(template, timeout, api_key, api_url, retries, base_backoff=3.0):
    """创建沙箱，对可重试错误做指数退避 + 抖动重试。"""
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return Sandbox.create(
                template=template, timeout=timeout, api_key=api_key, api_url=api_url
            )
        except Exception as e:
            last_exc = e
            if attempt >= retries or not _is_retriable_error(e):
                raise
            wait = base_backoff * (2 ** attempt) + random.uniform(0, base_backoff)
            print(f"    ⚠️ 创建失败（{e}），{wait:.1f}s 后重试（{attempt + 1}/{retries}）...")
            time.sleep(wait)
    raise last_exc


def _create_and_verify(template, timeout, api_key, api_url, retries):
    """创建单个沙箱并执行测试代码 + 系统信息，返回 (sandbox, system_info)。"""
    sandbox = _create_with_retry(template, timeout, api_key, api_url, retries=retries)
    try:
        sandbox.run_code(TEST_CODE, timeout=60)
        info_result = sandbox.run_code(SYSTEM_INFO_CODE, timeout=60)
        return sandbox, _extract_stdout(info_result)
    except Exception:
        # 代码执行失败时立即回收该沙箱，避免泄漏
        try:
            sandbox.kill()
        except Exception:
            pass
        raise


def _run_single_test(api_url, api_key, template):
    """单沙箱基础测试（控制台输出）。"""
    print("🚀 开始 Cube Sandbox 基础测试")
    print(f"📋 沙箱模板 ID: {template}")
    print(f"🌐 Cube API: {api_url}")

    sandbox = None
    try:
        print("\n[1/3] 创建沙箱...")
        sandbox = Sandbox.create(
            template=template, timeout=3600, api_key=api_key, api_url=api_url
        )
        print(f"✅ 沙箱创建成功: {sandbox.sandbox_id}")

        print("\n[2/3] 执行测试代码...")
        result = sandbox.run_code(TEST_CODE)
        print(f"✅ 代码执行结果: {result}")

        print("\n[3/3] 验证沙箱功能...")
        info_result = sandbox.run_code(SYSTEM_INFO_CODE, timeout=60)
        print(f"✅ 系统信息: {info_result}")

        print("\n🎉 所有测试通过！Cube Sandbox 运行正常。")

    except Exception as e:
        print(f"\n❌ 错误: {type(e).__name__}: {e}")
        sys.exit(1)

    finally:
        if sandbox:
            try:
                print("\n🧹 清理沙箱资源...")
                sandbox.kill()
                print("✅ 沙箱已清理")
            except Exception as e:
                print(f"⚠️ 清理沙箱时出错: {e}")


def _worker(idx, sandboxes, results, lock, api_url, api_key, template, retries):
    """并发 worker：创建沙箱并测量耗时。"""
    start_time = time.time()
    sandbox = None
    try:
        sandbox, system_info = _create_and_verify(template, 3600, api_key, api_url, retries)
        duration = time.time() - start_time
        with lock:
            sandboxes[idx] = sandbox
            results[idx] = {
                "sandbox_id": sandbox.sandbox_id,
                "system_info": system_info,
                "duration": duration,
                "success": True,
                "error": None,
            }
    except Exception as e:
        duration = time.time() - start_time
        with lock:
            results[idx] = {
                "sandbox_id": None,
                "system_info": "N/A",
                "duration": duration,
                "success": False,
                "error": str(e),
            }


def _compute_stats(results):
    """计算并发测试的统计指标。"""
    successes = [r for r in results.values() if r["success"]]
    failures = [r for r in results.values() if not r["success"]]
    durations = sorted(r["duration"] for r in successes)

    if not durations:
        return {
            "success": 0, "failed": len(failures),
            "min": 0.0, "max": 0.0, "avg": 0.0, "p95": 0.0, "p99": 0.0,
        }

    def percentile(seq, p):
        idx = min(int(len(seq) * p), len(seq) - 1)
        return seq[idx]

    return {
        "success": len(successes),
        "failed": len(failures),
        "min": durations[0],
        "max": durations[-1],
        "avg": sum(durations) / len(durations),
        "p95": percentile(durations, 0.95),
        "p99": percentile(durations, 0.99),
    }

def _generate_html_report(concurrency, total_time, stats, results):
    """生成 HTML 格式的并发启动性能测试报告。"""
    rows = ""
    for idx in sorted(results):
        r = results[idx]
        status = "✅ 成功" if r["success"] else "❌ 失败"
        color = "#4caf50" if r["success"] else "#f44336"
        sid = r["sandbox_id"] or "N/A"
        sys_info = html.escape(r["system_info"] or "N/A").replace("\n", "<br>")
        err = html.escape(r["error"] or "")
        rows += (
            f"<tr><td>{idx + 1}</td><td>{sid}</td>"
            f"<td style=\"color:{color};\">{status}</td>"
            f"<td>{r['duration']:.2f}s</td>"
            f"<td class=\"sysinfo\">{sys_info}</td>"
            f"<td>{err}</td></tr>"
        )

    html_report = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cube Sandbox 并发启动性能测试报告</title>
<style>
body{{font-family:'Segoe UI',Tahoma,sans-serif;background:#f5f7fa;margin:0;padding:20px;}}
.container{{max-width:1200px;margin:0 auto;}}
h1{{color:#2c3e50;text-align:center;}}
.summary{{background:#fff;border-radius:8px;padding:20px;margin:20px 0;box-shadow:0 2px 4px rgba(0,0,0,.1);}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:15px;margin:20px 0;}}
.metric-card{{background:#f8f9fa;border-radius:8px;padding:15px;text-align:center;}}
.metric-value{{font-size:24px;font-weight:bold;color:#3498db;}}
.metric-label{{font-size:14px;color:#7f8c8d;}}
table{{width:100%;border-collapse:collapse;margin:20px 0;}}
th,td{{padding:10px;text-align:left;border-bottom:1px solid #ddd;font-size:14px;}}
th{{background:#3498db;color:#fff;}}
tr:hover{{background:#f5f5f5;}}
.sysinfo{{font-family:monospace;font-size:12px;}}
</style></head><body>
<div class="container">
<h1>🚀 Cube Sandbox 并发启动性能测试报告</h1>
<div class="summary"><h2>📊 测试概览</h2>
<div class="metrics">
<div class="metric-card"><div class="metric-value">{concurrency}</div><div class="metric-label">并发数量</div></div>
<div class="metric-card"><div class="metric-value">{total_time:.2f}s</div><div class="metric-label">总耗时</div></div>
<div class="metric-card"><div class="metric-value" style="color:#4caf50;">{stats['success']}</div><div class="metric-label">成功</div></div>
<div class="metric-card"><div class="metric-value" style="color:#f44336;">{stats['failed']}</div><div class="metric-label">失败</div></div>
<div class="metric-card"><div class="metric-value">{stats['min']:.2f}s</div><div class="metric-label">最小耗时</div></div>
<div class="metric-card"><div class="metric-value">{stats['max']:.2f}s</div><div class="metric-label">最大耗时</div></div>
<div class="metric-card"><div class="metric-value">{stats['avg']:.2f}s</div><div class="metric-label">平均耗时</div></div>
<div class="metric-card"><div class="metric-value">{stats['p95']:.2f}s</div><div class="metric-label">P95</div></div>
<div class="metric-card"><div class="metric-value">{stats['p99']:.2f}s</div><div class="metric-label">P99</div></div>
</div></div>
<table><thead><tr><th>#</th><th>沙箱 ID</th><th>状态</th><th>耗时</th><th>系统信息</th><th>错误</th></tr></thead>
<tbody>{rows}</tbody></table>
</div></body></html>"""
    return html_report


def _run_concurrent_test(concurrency, api_url, api_key, template, retries):
    """并发启动性能测试。"""
    print(f"🚀 开始并发启动测试：并发数 = {concurrency}")
    print(f"📋 沙箱模板 ID: {template}")
    print(f"🌐 Cube API: {api_url}")
    print(f"🔁 创建重试次数: {retries}")
    print("=" * 60)

    sandboxes = {}
    results = {}
    lock = threading.Lock()
    start_all = time.time()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(_worker, i, sandboxes, results, lock, api_url, api_key, template, retries)
            for i in range(concurrency)
        ]
        for future in futures:
            future.result()

    total_time = time.time() - start_all
    stats = _compute_stats(results)

    print("\n📊 测试完成！")
    print(f"总耗时: {total_time:.2f}s")
    print(f"成功: {stats['success']}, 失败: {stats['failed']}")
    print(f"Min: {stats['min']:.2f}s, Max: {stats['max']:.2f}s, Avg: {stats['avg']:.2f}s")
    print(f"P95: {stats['p95']:.2f}s, P99: {stats['p99']:.2f}s")

    timeout_errors = [
        r for r in results.values()
        if not r["success"] and (r["error"] or "").startswith("408")
    ]
    if timeout_errors:
        print("\n⚠️ 检测到 408 请求超时：")
        print("   Cube 服务端在 30 秒内未能完成并发创建（预置资源池/预热点不足所致）。")
        print("   建议在 Cube 部署侧增大创建超时（CubeMaster conf.yaml 的 common_timeout_insec）")
        print("   或扩容预置资源池/预热点数量后重试。")

    report_filename = f"cube_sandbox_performance_report_{int(time.time())}.html"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(_generate_html_report(concurrency, total_time, stats, results))
    print(f"📄 HTML 报告已保存至: {report_filename}")

    print("\n🧹 清理所有沙箱资源...")
    for idx, sandbox in sandboxes.items():
        try:
            sandbox.kill()
        except Exception as e:
            print(f"⚠️ 清理沙箱 #{idx + 1} 失败: {e}")
    print("✅ 沙箱已清理")


def main():
    """主函数：解析命令行参数并运行测试。"""
    parser = argparse.ArgumentParser(
        description="Cube Sandbox 测试脚本（本地自托管 Cube Sandbox）",
        epilog="示例: python cube-sandbox-test.py -c 10  # 并发启动 10 个沙箱",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-c", "--concurrency", type=int, default=1,
        help="并发沙箱数量（默认 1，即单沙箱基础测试）",
    )
    parser.add_argument("--retry", type=int, default=2,
                        help="创建失败时的重试次数（默认 2，针对 408/429/5xx 错误）")
    parser.add_argument("--api-url", type=str, default=None,
                        help="Cube API Server 地址（覆盖 E2B_API_URL）")
    parser.add_argument("--api-key", type=str, default=None,
                        help="API 密钥（覆盖 E2B_API_KEY）")
    parser.add_argument("--template", type=str, default=None,
                        help="沙箱模板 ID（覆盖 CUBE_TEMPLATE_ID）")

    args = parser.parse_args()
    api_url, api_key, template = _resolve_config(args)

    if args.concurrency <= 1:
        _run_single_test(api_url, api_key, template)
    else:
        _run_concurrent_test(args.concurrency, api_url, api_key, template, args.retry)


if __name__ == "__main__":
    main()