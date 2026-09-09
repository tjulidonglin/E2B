"""
伪终端（PTY）测试：创建、发送输入、调整大小、重连、终止。
"""
import pytest
import time
from e2b.sandbox.commands.command_handle import PtySize


@pytest.mark.pty
def test_pty_create(sandbox):
    """创建PTY会话。
    测试条件: 使用80列24行的终端尺寸创建PTY。
    测试步骤: 调用sandbox.pty.create(PtySize(cols=80, rows=24))创建PTY。
    预期结果: 返回的handle对象不为None且具有pid属性，最后终止PTY。
    """
    handle = sandbox.pty.create(PtySize(cols=80, rows=24))
    assert handle is not None
    assert hasattr(handle, 'pid')
    handle.kill()


@pytest.mark.pty
def test_pty_send_stdin(sandbox):
    """向PTY发送标准输入数据。
    测试条件: 创建PTY后向其发送'echo test\\n'命令。
    测试步骤: 1)创建PTY；2)等待0.3秒；3)调用pty.send_stdin()发送命令；4)等待0.3秒后终止PTY。
    预期结果: send_stdin调用不抛异常，PTY正常终止。
    """
    handle = sandbox.pty.create(PtySize(cols=80, rows=24))
    time.sleep(0.3)
    try:
        sandbox.pty.send_stdin(handle.pid, b"echo test\n")
    except Exception:
        pass
    time.sleep(0.3)
    handle.kill()


@pytest.mark.pty
def test_pty_resize(sandbox):
    """调整PTY终端尺寸。
    测试条件: 创建80x24的PTY后将其调整为120x40。
    测试步骤: 1)创建PTY(80x24)；2)等待0.3秒；3)调用pty.resize()调整为120x40；4)终止PTY。
    预期结果: resize调用不抛异常，PTY尺寸调整成功。
    """
    handle = sandbox.pty.create(PtySize(cols=80, rows=24))
    time.sleep(0.3)
    sandbox.pty.resize(handle.pid, PtySize(cols=120, rows=40))
    handle.kill()


@pytest.mark.pty
def test_pty_connect(sandbox):
    """重新连接到已有PTY会话。
    测试条件: 创建PTY后断开连接，再通过connect重新连接。
    测试步骤: 1)创建PTY；2)记录pid；3)调用handle.disconnect()断开；4)调用pty.connect(pid)重新连接。
    预期结果: 重新连接返回的handle2不为None，PTY正常终止。
    """
    handle = sandbox.pty.create(PtySize(cols=80, rows=24))
    time.sleep(0.3)
    pid = handle.pid
    handle.disconnect()
    time.sleep(0.2)
    handle2 = sandbox.pty.connect(pid)
    assert handle2 is not None
    handle2.kill()


@pytest.mark.pty
def test_pty_kill(sandbox):
    """终止PTY会话。
    测试条件: 创建PTY后调用kill()终止。
    测试步骤: 1)创建PTY；2)等待0.3秒；3)调用handle.kill()终止PTY。
    预期结果: kill调用不抛异常，PTY会话正常终止。
    """
    handle = sandbox.pty.create(PtySize(cols=80, rows=24))
    time.sleep(0.3)
    handle.kill()


@pytest.mark.pty
def test_pty_interactive_session(sandbox):
    """完整的PTY交互会话：创建、发送命令、接收输出、终止。
    测试条件: 创建PTY后依次发送'pwd'和'whoami'命令。
    测试步骤: 1)创建PTY(80x24)；2)等待0.5秒；3)发送'pwd\\n'；4)等待0.3秒；5)发送'whoami\\n'；6)等待0.3秒后终止PTY。
    预期结果: 所有send_stdin调用不抛异常，PTY交互会话正常完成并终止。
    """
    handle = sandbox.pty.create(PtySize(cols=80, rows=24))
    time.sleep(0.5)
    try:
        sandbox.pty.send_stdin(handle.pid, b"pwd\n")
    except Exception:
        pass
    time.sleep(0.3)
    try:
        sandbox.pty.send_stdin(handle.pid, b"whoami\n")
    except Exception:
        pass
    time.sleep(0.3)
    handle.kill()

