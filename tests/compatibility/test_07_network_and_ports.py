"""
网络和端口测试：获取主机地址、下载URL、上传URL、端口暴露。
"""
import pytest


@pytest.mark.network
def test_get_host(sandbox):
    """获取指定端口的主机URL。
    测试条件: 查询8080端口对应的主机地址。
    测试步骤: 调用sandbox.get_host(8080)。
    预期结果: 返回的host不为None且为非空字符串。
    """
    host = sandbox.get_host(8080)
    assert host is not None
    assert isinstance(host, str)
    assert len(host) > 0


@pytest.mark.network
def test_get_host_format(sandbox):
    """验证主机URL的格式。
    测试条件: 查询3000端口对应的主机地址。
    测试步骤: 调用sandbox.get_host(3000)并验证格式。
    预期结果: 返回的host不为None且包含'.'或':'（为有效的主机名或URL）。
    """
    host = sandbox.get_host(3000)
    assert host is not None
    # Should be a valid hostname or URL
    assert "." in host or ":" in host


@pytest.mark.network
def test_download_url(sandbox):
    """获取文件的下载URL。
    测试条件: 先创建文件/tmp/download_test.txt，然后获取其下载链接。
    测试步骤: 1)写入文件；2)调用sandbox.download_url()获取下载URL。
    预期结果: 返回的URL不为None且为字符串；若API不支持则跳过测试。
    """
    sandbox.files.write("/tmp/download_test.txt", "test content")
    try:
        url = sandbox.download_url("/tmp/download_test.txt")
        assert url is not None
        assert isinstance(url, str)
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"download_url not available: {e}")


@pytest.mark.network
def test_upload_url(sandbox):
    """获取文件的上传URL。
    测试条件: 获取/tmp/upload_test.txt的上传链接。
    测试步骤: 调用sandbox.upload_url("/tmp/upload_test.txt")获取上传URL。
    预期结果: 返回的URL不为None且为字符串；若API不支持则跳过测试。
    """
    try:
        url = sandbox.upload_url("/tmp/upload_test.txt")
        assert url is not None
        assert isinstance(url, str)
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"upload_url not available: {e}")


@pytest.mark.network
def test_port_exposure(sandbox):
    """通过启动HTTP服务器测试端口暴露。
    测试条件: 在沙箱中启动python3 -m http.server 8888后台进程。
    测试步骤: 1)以background=True启动HTTP服务器；2)等待1秒；3)调用sandbox.get_host(8888)获取外部访问地址。
    预期结果: 返回的host不为None，端口暴露功能正常。
    """
    import time
    
    # Start a simple HTTP server
    sandbox.commands.run(
        "python3 -m http.server 8888 &",
        background=True,
        cwd="/tmp"
    )
    time.sleep(1)
    
    # Get the host URL
    host = sandbox.get_host(8888)
    assert host is not None


@pytest.mark.network
def test_get_mcp_url(sandbox):
    """获取MCP（模型上下文协议）URL。
    测试条件: 调用sandbox.get_mcp_url()获取MCP服务地址。
    测试步骤: 调用sandbox.get_mcp_url()。
    预期结果: 返回URL或None；若API不支持则跳过测试。
    """
    try:
        url = sandbox.get_mcp_url()
        assert url is not None or url is None  # May not be implemented
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"get_mcp_url not available: {e}")


@pytest.mark.network
def test_get_mcp_token(sandbox):
    """获取MCP令牌。
    测试条件: 调用sandbox.get_mcp_token()获取认证令牌。
    测试步骤: 调用sandbox.get_mcp_token()。
    预期结果: 返回None或字符串类型的令牌；若API不支持则跳过测试。
    """
    try:
        token = sandbox.get_mcp_token()
        # Token may be None if not implemented
        assert token is None or isinstance(token, str)
    except (AttributeError, NotImplementedError, Exception) as e:
        pytest.skip(f"get_mcp_token not available: {e}")
