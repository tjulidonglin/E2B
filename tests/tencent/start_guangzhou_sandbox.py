# -*- coding: utf-8 -*-
"""
广州区域 Agent 沙箱并发启动性能测试脚本

- 地域: 广州 (ap-guangzhou)
- 沙箱工具: code-2qwk4i22zs4（sdt-5ujfu47h）
- 功能: 测试并发启动沙箱的性能指标
- 配置: 通过环境变量配置，无需修改代码
  - E2B_DOMAIN: 腾讯云沙箱域名 (默认: ap-guangzhou.tencentags.com)
  - E2B_API_KEY: 腾讯云 API Key
  - SANDBOX_TEMPLATE: 沙箱模板 ID (默认: code-2qwk4i22zs4)

使用方法:
  python tests/tencent/start_guangzhou_sandbox.py -c 10  # 10 并发
  python tests/tencent/start_guangzhou_sandbox.py --help  # 查看帮助
"""

import os
import sys
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 添加项目根目录到路径，以便导入其他模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from e2b_code_interpreter import Sandbox

# 从环境变量读取配置，优先使用环境变量，否则使用默认值
TENCENT_DOMAIN = os.environ.get("E2B_DOMAIN", "ap-guangzhou.tencentags.com")
TENCENT_API_KEY = os.environ.get("E2B_API_KEY")
if not TENCENT_API_KEY:
    print("警告: 未设置 E2B_API_KEY 环境变量")
    print("请通过以下方式设置:")
    print("  export E2B_API_KEY='your-api-key'")
    print("  或在命令行中指定 --api-key 参数")
    sys.exit(1)

# 从环境变量获取沙箱 template，默认为 code-2qwk4i22zs4
SANDBOX_TEMPLATE = os.environ.get("SANDBOX_TEMPLATE", "code-2qwk4i22zs4")


def _get_output(result, field='logs'):
    """安全地获取沙箱执行结果"""
    try:
        if hasattr(result, 'text') and result.text:
            return result.text.strip()
        if hasattr(result, 'results') and result.results:
            return str(result.results[0])
        if hasattr(result, field) and hasattr(getattr(result, field), 'stdout'):
            stdout = getattr(result, field).stdout
            if stdout:
                return stdout[0].strip() if isinstance(stdout, list) else str(stdout)
    except Exception:
        pass
    return "N/A"


def _query_kernel_version(sandbox):
    """查询沙箱内部内核版本号"""
    try:
        result = sandbox.run_code(
            "import subprocess; print(subprocess.run('uname -r', shell=True, capture_output=True, text=True).stdout.strip())",
            timeout=600
        )
        return _get_output(result)
    except Exception:
        return "N/A"


def _query_memory_info(sandbox):
    """查询沙箱内部内存使用信息（系统内存 + RSS + PSS）"""
    try:
        memory_result = sandbox.run_code("""
import os

# 获取系统内存信息
mem_info = {}
with open('/proc/meminfo', 'r') as f:
    for line in f:
        key, value = line.split(':')
        mem_info[key.strip()] = value.strip()

# 获取当前进程 RSS 和 PSS 内存信息
proc_status = {}
with open('/proc/self/status', 'r') as f:
    for line in f:
        if line.startswith(('VmRSS:', 'VmPSS:')):
            key, value = line.split(':')
            proc_status[key.strip()] = value.strip()

# 格式化输出系统内存信息
print("=== 系统内存信息 ===")
print(f"总内存：{mem_info.get('MemTotal', 'N/A')}")
print(f"可用内存：{mem_info.get('MemAvailable', 'N/A')}")
print(f"MemFree：{mem_info.get('MemFree', 'N/A')}")
print(f"缓存：{mem_info.get('Cached', 'N/A')}")
print(f"缓冲区：{mem_info.get('Buffers', 'N/A')}")
print("")

# 格式化输出进程内存信息（RSS 和 PSS）
print("=== 进程内存信息（RSS 和 PSS）===")
print(f"RSS（驻留集大小）：{proc_status.get('VmRSS', 'N/A')}")
print(f"PSS（按比例驻留集大小）：{proc_status.get('VmPSS', 'N/A')}")
""", timeout=600)
        return _get_output(memory_result)
    except Exception:
        return "N/A"


def create_and_measure_sandbox(idx, sandboxes, results, lock):
    """创建并测量单个沙箱的性能指标"""
    start_time = time.time()
    sandbox = None
    try:
        sandbox = Sandbox.create(
            template=SANDBOX_TEMPLATE,
            timeout=3600,
            api_key=TENCENT_API_KEY,
            domain=TENCENT_DOMAIN
        )
        # 查询沙箱内部内核版本号和内存信息
        kernel_version = _query_kernel_version(sandbox)
        memory_info = _query_memory_info(sandbox)

        end_time = time.time()
        with lock:
            sandboxes[idx] = sandbox
            results[idx] = {
                'sandbox_id': sandbox.sandbox_id,
                'kernel_version': kernel_version,
                'memory_info': memory_info,
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'success': True,
                'error': None
            }
    except Exception as e:
        end_time = time.time()
        with lock:
            results[idx] = {
                'sandbox_id': None,
                'start_time': start_time,
                'end_time': end_time,
                'duration': end_time - start_time,
                'success': False,
                'error': str(e)
            }


def generate_html_report(concurrency, total_time, success_count, failed_count,
                         min_time, max_time, avg_time, p95_time, p99_time, results):
    """生成 HTML 格式的性能测试报告"""
    rows = ""
    for idx, r in sorted(results.items(), key=lambda x: x[0]):
        st = "✅ 成功" if r['success'] else "❌ 失败"
        sc = "#4caf50" if r['success'] else "#f44336"
        sid = r['sandbox_id'] if r['sandbox_id'] else "N/A"
        kv = r.get('kernel_version', 'N/A')
        mi = r.get('memory_info', 'N/A').replace('\n', '<br>')
        em = r['error'] if r['error'] else ""
        rows += f"""<tr><td>{idx + 1}</td><td>{sid}</td><td style="color: {sc};">{st}</td><td>{r['duration']:.2f}s</td><td>{kv}</td><td>{mi}</td><td>{em}</td></tr>"""
    
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>沙箱并发启动性能测试报告</title><style>body{{font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background-color:#f5f7fa;margin:0;padding:20px;}}.container{{max-width:1200px;margin:0 auto;}}h1{{color:#2c3e50;text-align:center;}}.summary{{background:white;border-radius:8px;padding:20px;margin:20px 0;box-shadow:0 2px 4px rgba(0,0,0,0.1);}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:15px;margin:20px 0;}}.metric-card{{background:#f8f9fa;border-radius:8px;padding:15px;text-align:center;}}.metric-value{{font-size:24px;font-weight:bold;color:#3498db;}}.metric-label{{font-size:14px;color:#7f8c8d;}}table{{width:100%;border-collapse:collapse;margin:20px 0;}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #ddd;}}th{{background-color:#3498db;color:white;}}tr:hover{{background-color:#f5f5f5;}}.memory-info{{font-family:monospace;font-size:12px;background:#f8f9fa;padding:8px;border-radius:4px;white-space:pre-wrap;}}</style></head><body><div class="container"><h1>🚀 沙箱并发启动性能测试报告</h1><div class="summary"><h2>📊 测试概览</h2><div class="metrics"><div class="metric-card"><div class="metric-value">{concurrency}</div><div class="metric-label">并发数量</div></div><div class="metric-card"><div class="metric-value">{total_time:.2f}s</div><div class="metric-label">总耗时</div></div><div class="metric-card"><div class="metric-value" style="color: #4caf50;">{success_count}</div><div class="metric-label">成功</div></div><div class="metric-card"><div class="metric-value" style="color: #f44336;">{failed_count}</div><div class="metric-label">失败</div></div><div class="metric-card"><div class="metric-value">{min_time:.2f}s</div><div class="metric-label">最小耗时</div></div><div class="metric-card"><div class="metric-value">{max_time:.2f}s</div><div class="metric-label">最大耗时</div></div><div class="metric-card"><div class="metric-value">{avg_time:.2f}s</div><div class="metric-label">平均耗时</div></div><div class="metric-card"><div class="metric-value">{p95_time:.2f}s</div><div class="metric-label">P95 耗时</div></div><div class="metric-card"><div class="metric-value">{p99_time:.2f}s</div><div class="metric-label">P99 耗时</div></div></div></div><h2>📋 详细信息</h2><table><thead><tr><th>#</th><th>Sandbox ID</th><th>状态</th><th>耗时</th><th>内核版本</th><th>内存信息</th><th>错误信息</th></tr></thead><tbody>{rows}</tbody></table></div></body></html>"""
    return html


def main():
    """主函数：执行广州区域沙箱并发启动性能测试"""
    parser = argparse.ArgumentParser(
        description='广州区域沙箱并发启动性能测试',
        epilog='示例: python tests/tencent/start_guangzhou_sandbox.py -c 10',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-c', '--concurrency', type=int, default=10,
                        help='并发沙箱数量（默认10）')
    parser.add_argument('--template', type=str, default=None,
                        help='沙箱模板 ID（默认: code-2qwk4i22zs4）')
    parser.add_argument('--api-key', type=str, default=None,
                        help='E2B API Key（默认从环境变量读取）')
    parser.add_argument('--domain', type=str, default=None,
                        help='腾讯云沙箱域名（默认: ap-guangzhou.tencentags.com）')
    parser.add_argument('--wait-time', type=int, default=5,
                        help='清理前等待时间（秒，默认5）')
    
    args = parser.parse_args()
    
    # 使用命令行参数覆盖环境变量
    if args.template:
        global SANDBOX_TEMPLATE
        SANDBOX_TEMPLATE = args.template
    if args.api_key:
        global TENCENT_API_KEY
        TENCENT_API_KEY = args.api_key
    if args.domain:
        global TENCENT_DOMAIN
        TENCENT_DOMAIN = args.domain
    
    concurrency = args.concurrency
    print(f"🚀 开始测试：并发数 = {concurrency}")
    print(f"📋 沙箱模板 ID: {SANDBOX_TEMPLATE}")
    print(f"🌐 域名: {TENCENT_DOMAIN}")
    print(f"⏱ 清理等待时间: {args.wait_time}s")
    print("=" * 60)
    
    sandboxes = {}
    results = {}
    lock = threading.Lock()
    start_all_time = time.time()
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(concurrency):
            future = executor.submit(create_and_measure_sandbox, i, sandboxes, results, lock)
            futures.append(future)
        for future in futures:
            future.result()
    
    total_time = time.time() - start_all_time
    
    # 沙箱测试完成后，等待指定时间再统一清理沙箱资源
    print(f"\n⏳ 等待 {args.wait_time} 秒后清理沙箱资源...")
    time.sleep(args.wait_time)
    
    print("\n🧹 统一清理所有沙箱资源...")
    for sandbox in sandboxes.values():
        try:
            sandbox.kill()
        except Exception as e:
            print(f"清理沙箱失败: {e}")
    
    # 计算统计信息
    success_results = [r for r in results.values() if r['success']]
    failed_results = [r for r in results.values() if not r['success']]
    durations = [r['duration'] for r in success_results]
    
    if durations:
        min_time = min(durations)
        max_time = max(durations)
        avg_time = sum(durations) / len(durations)
        sorted_durations = sorted(durations)
        p95_index = int(len(sorted_durations) * 0.95)
        p99_index = int(len(sorted_durations) * 0.99)
        p95_time = sorted_durations[min(p95_index, len(sorted_durations) - 1)]
        p99_time = sorted_durations[min(p99_index, len(sorted_durations) - 1)]
    else:
        min_time = max_time = avg_time = p95_time = p99_time = 0
    
    # 生成并保存 HTML 报告
    html_report = generate_html_report(
        concurrency=concurrency,
        total_time=total_time,
        success_count=len(success_results),
        failed_count=len(failed_results),
        min_time=min_time,
        max_time=max_time,
        avg_time=avg_time,
        p95_time=p95_time,
        p99_time=p99_time,
        results=results
    )
    
    report_filename = f"sandbox_performance_report_{int(time.time())}.html"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    print(f"\n📊 测试完成！")
    print(f"总耗时: {total_time:.2f}s")
    print(f"成功: {len(success_results)}, 失败: {len(failed_results)}")
    print(f"Min: {min_time:.2f}s, Max: {max_time:.2f}s, Avg: {avg_time:.2f}s")
    print(f"P95: {p95_time:.2f}s, P99: {p99_time:.2f}s")
    print(f"\n📄 HTML 报告已保存至: {report_filename}")


if __name__ == "__main__":
    main()
