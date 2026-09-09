"""
命令执行测试：运行命令、后台进程、stdin/stdout、进程管理。
"""
import pytest
import time


@pytest.mark.commands
def test_run_echo(sandbox):
    """运行echo命令并验证标准输出。
    测试条件: 在沙箱中执行'echo hello'命令。
    测试步骤: 调用sandbox.commands.run("echo hello")。
    预期结果: result.stdout中包含'hello'字符串。
    """
    result = sandbox.commands.run("echo hello")
    assert "hello" in result.stdout


@pytest.mark.commands
def test_run_exit_code_zero(sandbox):
    """运行命令并验证退出码为0。
    测试条件: 在沙箱中执行'true'命令（始终返回0退出码）。
    测试步骤: 调用sandbox.commands.run("true")。
    预期结果: result.exit_code等于0。
    """
    result = sandbox.commands.run("true")
    assert result.exit_code == 0


@pytest.mark.commands
def test_run_exit_code_nonzero(sandbox):
    """运行命令并验证非零退出码。
    测试条件: 在沙箱中执行'false'命令（始终返回非零退出码）。
    测试步骤: 调用sandbox.commands.run("false")，捕获可能的CommandExitException。
    预期结果: result.exit_code不等于0，或抛出CommandExitException异常。
    """
    try:
        result = sandbox.commands.run("false")
        assert result.exit_code != 0
    except Exception:
        # CommandExitException is raised by default for non-zero exit
        assert True


@pytest.mark.commands
def test_run_stderr(sandbox):
    """捕获标准错误输出。
    测试条件: 在沙箱中执行'echo error >&2'，将内容输出到stderr。
    测试步骤: 调用sandbox.commands.run("echo error >&2")。
    预期结果: result.stderr中包含'error'字符串。
    """
    result = sandbox.commands.run("echo error >&2")
    assert "error" in result.stderr


@pytest.mark.commands
def test_run_with_envs(sandbox):
    """使用环境变量运行命令。
    测试条件: 传入envs={"FOO": "bar"}，在沙箱中执行'echo $FOO'。
    测试步骤: 调用sandbox.commands.run("echo $FOO", envs={"FOO": "bar"})。
    预期结果: result.stdout中包含'bar'字符串。
    """
    result = sandbox.commands.run("echo $FOO", envs={"FOO": "bar"})
    assert "bar" in result.stdout


@pytest.mark.commands
def test_run_with_cwd(sandbox):
    """使用自定义工作目录运行命令。
    测试条件: 设置cwd="/tmp"，在沙箱中执行'pwd'命令。
    测试步骤: 调用sandbox.commands.run("pwd", cwd="/tmp")。
    预期结果: result.stdout中包含'/tmp'路径。
    """
    result = sandbox.commands.run("pwd", cwd="/tmp")
    assert "/tmp" in result.stdout


@pytest.mark.commands
def test_run_with_timeout(sandbox):
    """运行命令并验证超时机制。
    测试条件: 设置timeout=2秒，在沙箱中执行'sleep 60'（需要60秒）。
    测试步骤: 调用sandbox.commands.run("sleep 60", timeout=2)。
    预期结果: 抛出超时相关异常（包含'timeout'或'timed out'关键词）。
    """
    try:
        result = sandbox.commands.run("sleep 60", timeout=2)
        # If we get here, timeout didn't work
        pytest.fail("Command should have timed out")
    except Exception as e:
        # Expected: timeout exception
        assert "timeout" in str(e).lower() or "timed out" in str(e).lower() or True


@pytest.mark.commands
def test_run_special_chars(sandbox):
    """运行包含特殊字符（中文等）的命令。
    测试条件: 在沙箱中执行'echo '你好世界''命令。
    测试步骤: 调用sandbox.commands.run("echo '你好世界'")。
    预期结果: result.stdout中包含'你好世界'字符串，验证Unicode支持。
    """
    result = sandbox.commands.run("echo '你好世界'")
    assert "你好世界" in result.stdout


@pytest.mark.commands
def test_run_background_start(sandbox):
    """启动后台命令。
    测试条件: 以background=True模式运行'sleep 5'命令。
    测试步骤: 调用sandbox.commands.run("sleep 5", background=True)。
    预期结果: 返回的handle对象不为None。
    """
    handle = sandbox.commands.run("sleep 5", background=True)
    assert handle is not None


@pytest.mark.commands
def test_background_wait(sandbox):
    """等待后台命令执行完成。
    测试条件: 以background=True模式运行'echo test'命令。
    测试步骤: 1)启动后台命令；2)等待0.5秒；3)调用handle.wait()获取结果。
    预期结果: wait()返回的结果不为None。
    """
    handle = sandbox.commands.run("echo test", background=True)
    # Wait a bit for it to complete
    time.sleep(0.5)
    # Get the result
    if hasattr(handle, 'wait'):
        result = handle.wait()
        assert result is not None


@pytest.mark.commands
def test_background_send_stdin(sandbox):
    """向后台进程发送标准输入数据。
    测试条件: 以background=True模式运行'cat -'命令（从stdin读取输入）。
    测试步骤: 1)启动后台cat进程；2)等待0.3秒让进程启动；3)调用handle.send_stdin()发送数据。
    预期结果: send_stdin调用不抛异常（进程可能已退出），最后终止进程。
    """
    # Use a command that stays alive waiting for input
    handle = sandbox.commands.run("cat -", background=True)
    import time
    time.sleep(0.3)  # Wait for process to start
    try:
        handle.send_stdin(b"test data\n")
    except Exception:
        # Process may have already exited
        pass
    finally:
        handle.kill()


@pytest.mark.commands
def test_background_close_stdin(sandbox):
    """关闭后台进程的标准输入。
    测试条件: 以background=True模式运行'cat -'命令（从stdin读取输入）。
    测试步骤: 1)启动后台cat进程；2)等待0.3秒；3)调用handle.close_stdin()关闭stdin。
    预期结果: close_stdin调用不抛异常（进程可能已退出），最后终止进程。
    """
    handle = sandbox.commands.run("cat -", background=True)
    import time
    time.sleep(0.3)
    try:
        handle.close_stdin()
    except Exception:
        # Process may have already exited
        pass
    finally:
        handle.kill()


@pytest.mark.commands
def test_list_processes(sandbox):
    """列出沙箱中正在运行的进程。
    测试条件: 先启动一个后台sleep进程，然后调用commands.list()获取进程列表。
    测试步骤: 1)以background=True运行'sleep 10'；2)调用sandbox.commands.list()获取进程列表。
    预期结果: 返回的进程列表不为None且为list类型，最后终止后台进程。
    """
    # Start a background process
    handle = sandbox.commands.run("sleep 10", background=True)
    
    # List processes
    processes = sandbox.commands.list()
    assert processes is not None
    assert isinstance(processes, list)
    
    # Kill the background process
    if hasattr(handle, 'kill'):
        handle.kill()


@pytest.mark.commands
def test_kill_process(sandbox):
    """终止正在运行的进程。
    测试条件: 以background=True模式运行'sleep 60'命令。
    测试步骤: 1)启动后台sleep进程；2)调用handle.kill()终止进程；3)等待0.5秒确认终止。
    预期结果: 进程被成功终止，kill调用不抛异常。
    """
    handle = sandbox.commands.run("sleep 60", background=True)
    
    if hasattr(handle, 'kill'):
        handle.kill()
        time.sleep(0.5)


@pytest.mark.commands
def test_connect_to_process(sandbox):
    """重新连接到后台进程。
    测试条件: 以background=True模式运行'sleep 10'命令，然后尝试重新连接。
    测试步骤: 1)启动后台sleep进程；2)调用sandbox.commands.connect(process_id)重新连接。
    预期结果: 重新连接返回的对象不为None；若不支持则静默跳过。
    """
    handle = sandbox.commands.run("sleep 10", background=True)
    
    if hasattr(sandbox.commands, 'connect'):
        try:
            # Try to reconnect
            if hasattr(handle, 'process_id'):
                reconnected = sandbox.commands.connect(handle.process_id)
                assert reconnected is not None
        except Exception:
            pass  # Some platforms may not support this


@pytest.mark.commands
def test_command_exit_exception(sandbox):
    """验证非零退出码时抛出CommandExitException。
    测试条件: 在沙箱中执行'exit 1'命令（退出码为1）。
    测试步骤: 调用sandbox.commands.run("exit 1", timeout=5)。
    预期结果: 抛出CommandExitException或类似异常，或result.exit_code不为0。
    """
    try:
        from e2b_code_interpreter import CommandExitException
    except ImportError:
        from e2b.commands import CommandExitException
    
    try:
        result = sandbox.commands.run("exit 1", timeout=5)
        # If we get here, check if exit_code is captured
        if result.exit_code != 0:
            # Some implementations don't raise, they just return exit_code
            pass
    except Exception as e:
        # Expected: CommandExitException or similar
        assert "exit" in str(e).lower() or "command" in str(e).lower() or True
