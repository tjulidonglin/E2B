"""
Huawei Cloud Patch for E2B Sandbox

This module provides patches for E2B sandbox to work with Huawei Cloud endpoints.
The patches handle:
1. Setting traffic_access_token for authentication
2. Enabling HTTP redirects for the sandbox client
3. Retry mechanism for transient network errors
"""

import os
import time
import httpx
from functools import wraps
from e2b.api.client_sync import get_transport
from e2b.envd.client_sync import create_rpc_client
from e2b.envd.process import process_connect
from e2b.envd.filesystem import filesystem_connect


# 华为云环境特征域名/关键字
HUAWEI_CLOUD_KEYWORDS = [
    "huaweicloud",
    "myhuaweicloud",
    "agentgateway",
    "huaweicloud-agentnetwork",
    "agentsphere",
]


def is_huawei_environment() -> bool:
    """
    判断当前是否为华为云 E2B 环境。
    
    通过检测环境变量中的 API URL / Sandbox URL 是否包含华为云特征域名来判断。
    标准 E2B（官方 api.e2b.dev）不会命中这些关键字，因此不会被误判。
    
    Returns:
        True 表示华为云环境，需要应用补丁
    """
    api_url = os.environ.get("E2B_API_URL", "")
    sandbox_url = os.environ.get("E2B_SANDBOX_URL", "")
    domain = os.environ.get("E2B_DOMAIN", "")
    
    combined = f"{api_url} {sandbox_url} {domain}".lower()
    return any(keyword in combined for keyword in HUAWEI_CLOUD_KEYWORDS)


def patch_sandbox_if_needed(sbx):
    """
    按需应用华为云补丁。仅当检测到华为云环境时才应用补丁，
    标准 E2B 环境保持原生行为，确保兼容性。
    
    Args:
        sbx: E2B Sandbox instance
        
    Returns:
        同一个 sandbox 实例（可能已打补丁）
    """
    if is_huawei_environment():
        return patch_sandbox_for_huawei(sbx)
    return sbx


# 可重试的错误类型
RETRYABLE_ERRORS = [
    "connection refused",
    "524",
    "502",
    "503",
    "504",
    "timeout",
    "reset by peer",
    "closed connection",
    "close_notify",
    "unexpected eof",
    "remote protocol",
]


def is_retryable_error(error: Exception) -> bool:
    """判断错误是否可以重试"""
    error_str = str(error).lower()
    return any(keyword in error_str for keyword in RETRYABLE_ERRORS)


def with_retry(max_retries: int = 3, delay: float = 2.0, backoff: float = 2.0):
    """
    重试装饰器，用于处理瞬时网络错误
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟时间的指数退避因子
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    
                    # 检查是否为可重试错误
                    if not is_retryable_error(e):
                        raise e
                    
                    # 最后一次尝试不再等待
                    if attempt == max_retries:
                        raise e
                    
                    print(f"    [Retry {attempt + 1}/{max_retries}] {type(e).__name__}: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_error
        return wrapper
    return decorator


def patch_sandbox_for_huawei(sbx):
    """
    Patch E2B sandbox for Huawei Cloud compatibility.
    
    This must be called after sandbox creation to:
    1. Set traffic_access_token in connection config headers
    2. Enable HTTP redirects for the sandbox client
    
    Args:
        sbx: E2B Sandbox instance
    """
    # Set traffic_access_token in headers
    if hasattr(sbx, 'traffic_access_token') and sbx.traffic_access_token:
        sbx.connection_config._ConnectionConfig__extra_sandbox_headers[
            "E2b-Traffic-Access-Token"
        ] = sbx.traffic_access_token
    
    # Patch client to follow redirects
    @property
    def _client_with_redirects(self):
        return httpx.Client(
            transport=get_transport(self.connection_config, http2=False),
            follow_redirects=True,
        )
    type(sbx)._client = _client_with_redirects
    
    # Create new HTTP clients with redirects enabled
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
    
    # Patch filesystem client if exists
    if hasattr(sbx, "_filesystem"):
        sbx._filesystem._envd_api = new_envd_api
        sbx._filesystem._envd_api_streaming = new_envd_streaming
        sbx._filesystem._rpc = create_rpc_client(
            filesystem_connect.FilesystemClientSync,
            sbx.envd_api_url,
            sbx.connection_config,
        )
    
    # Patch commands client if exists
    if hasattr(sbx, "_commands"):
        sbx._commands._envd_api = new_envd_api
        sbx._commands._rpc = create_rpc_client(
            process_connect.ProcessClientSync,
            sbx.envd_api_url,
            sbx.connection_config,
        )
    
    # Patch pty client if exists
    if hasattr(sbx, "_pty"):
        sbx._pty._envd_api = new_envd_api
    
    old.close()
    
    return sbx


def safe_kill_sandbox(sbx, sandbox_id: str = None):
    """
    安全地销毁 Sandbox，带有重试机制
    
    Args:
        sbx: Sandbox 实例
        sandbox_id: Sandbox ID（用于日志）
    """
    sandbox_id = sandbox_id or (sbx.sandbox_id[:12] if hasattr(sbx, 'sandbox_id') else 'unknown')
    
    for attempt in range(3):
        try:
            sbx.kill()
            return True
        except Exception as e:
            if attempt < 2:
                print(f"    [Kill retry {attempt + 1}] Sandbox {sandbox_id}... error: {e}")
                time.sleep(1)
            else:
                print(f"    [Kill failed] Sandbox {sandbox_id}: {e}")
                return False
    return False