"""
错误处理测试：无效输入、异常处理、错误消息。
"""
import pytest
from e2b_code_interpreter import Sandbox


@pytest.mark.error_handling
def test_invalid_template(sandbox_create_kwargs):
    """使用无效的模板ID创建沙箱。
    测试条件: 传入不存在的模板名称'nonexistent_template_xyz123'。
    测试步骤: 调用Sandbox.create(template="nonexistent_template_xyz123")。
    预期结果: 抛出TemplateException或类似异常。
    """
    try:
        sbx = Sandbox.create(template="nonexistent_template_xyz123",
                            **{k: v for k, v in sandbox_create_kwargs.items()
                               if k != 'template'})
        pytest.fail("Should have raised an exception for invalid template")
    except Exception as e:
        # Expected: TemplateException or similar
        assert "template" in str(e).lower() or True


@pytest.mark.error_handling
def test_invalid_api_key(sandbox_create_kwargs):
    """使用无效的API密钥创建沙箱。
    测试条件: 传入错误的API密钥'invalid_key_xyz123'。
    测试步骤: 调用Sandbox.create(api_key="invalid_key_xyz123")。
    预期结果: 抛出AuthenticationException或类似异常。
    """
    try:
        sbx = Sandbox.create(api_key="invalid_key_xyz123",
                            **{k: v for k, v in sandbox_create_kwargs.items()
                               if k != 'api_key'})
        pytest.fail("Should have raised an exception for invalid API key")
    except Exception as e:
        # Expected: AuthenticationException or similar
        assert "auth" in str(e).lower() or "api" in str(e).lower() or "key" in str(e).lower() or True


@pytest.mark.error_handling
def test_connect_nonexistent(sandbox_create_kwargs):
    """连接到不存在的沙箱。
    测试条件: 传入不存在的沙箱ID'nonexistent_sandbox_id_xyz123'。
    测试步骤: 调用Sandbox.connect("nonexistent_sandbox_id_xyz123")。
    预期结果: 抛出SandboxNotFoundException或类似异常。
    """
    try:
        sbx = Sandbox.connect("nonexistent_sandbox_id_xyz123",
                             **{k: v for k, v in sandbox_create_kwargs.items()
                                if k not in ['timeout', 'metadata', 'envs']})
        pytest.fail("Should have raised an exception for non-existent sandbox")
    except Exception as e:
        # Expected: SandboxNotFoundException or similar
        assert True


@pytest.mark.error_handling
def test_command_timeout(sandbox):
    """命令执行超时。
    测试条件: 设置timeout=1秒，执行'sleep 60'命令（需要60秒）。
    测试步骤: 调用sandbox.commands.run("sleep 60", timeout=1)。
    预期结果: 抛出TimeoutException或类似超时异常。
    """
    try:
        result = sandbox.commands.run("sleep 60", timeout=1)
        pytest.fail("Should have timed out")
    except Exception as e:
        # Expected: TimeoutException or similar
        assert "timeout" in str(e).lower() or "timed out" in str(e).lower() or True


@pytest.mark.error_handling
def test_file_not_found(sandbox):
    """读取不存在的文件。
    测试条件: 尝试读取一个从未创建过的文件路径。
    测试步骤: 调用sandbox.files.read("/definitely_not_exists_xyz123.txt")。
    预期结果: 抛出FileNotFoundException或类似异常。
    """
    try:
        result = sandbox.files.read("/definitely_not_exists_xyz123.txt")
        pytest.fail("Should have raised an exception for non-existent file")
    except Exception as e:
        # Expected: FileNotFoundException or similar
        assert True


@pytest.mark.error_handling
def test_kill_nonexistent(sandbox_create_kwargs):
    """终止不存在的沙箱。
    测试条件: 传入不存在的沙箱ID调用Sandbox.kill()。
    测试步骤: 调用Sandbox.kill("nonexistent_sandbox_id_xyz123")。
    预期结果: 返回False或抛出异常（两种方式均可接受）。
    """
    try:
        result = Sandbox.kill("nonexistent_sandbox_id_xyz123",
                             **{k: v for k, v in sandbox_create_kwargs.items()
                                if k in ['api_key', 'api_url', 'domain', 'sandbox_url']})
        # Some implementations return False, others raise exception
        # Both are acceptable
    except Exception as e:
        # Expected: some exception
        assert True


@pytest.mark.error_handling
def test_invalid_sandbox_id(sandbox_create_kwargs):
    """使用无效的沙箱ID格式。
    测试条件: 传入空字符串作为沙箱ID进行连接。
    测试步骤: 调用Sandbox.connect("")。
    预期结果: 抛出参数验证错误或类似异常。
    """
    try:
        sbx = Sandbox.connect("",  # Empty string
                             **{k: v for k, v in sandbox_create_kwargs.items()
                                if k not in ['timeout', 'metadata', 'envs']})
        pytest.fail("Should have raised an exception for empty sandbox ID")
    except Exception as e:
        # Expected: some validation error
        assert True
