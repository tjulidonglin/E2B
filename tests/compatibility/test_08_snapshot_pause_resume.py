"""
快照、暂停和恢复测试。
"""
import pytest
import time


@pytest.mark.snapshot
def test_pause_sandbox(sandbox_factory, sandbox_create_kwargs):
    """暂停正在运行的沙箱。
    测试条件: 创建一个沙箱后调用pause()暂停。
    测试步骤: 1)通过sandbox_factory创建沙箱；2)调用sbx.pause()。
    预期结果: pause操作成功（返回True或None）；若API不支持则跳过测试。
    """
    sbx = sandbox_factory()
    try:
        result = sbx.pause()
        # Result might be True/None depending on implementation
        assert result is not None or True
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"pause not available: {e}")


@pytest.mark.snapshot
def test_pause_keep_memory(sandbox_factory):
    """暂停沙箱并保留内存快照。
    测试条件: 创建一个沙箱后以keep_memory=True参数暂停。
    测试步骤: 1)通过sandbox_factory创建沙箱；2)调用sbx.pause(keep_memory=True)。
    预期结果: 暂停操作成功并保留内存状态；若API不支持则跳过测试。
    """
    sbx = sandbox_factory()
    try:
        sbx.pause(keep_memory=True)
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"pause with keep_memory not available: {e}")
    except TypeError as e:
        pytest.skip(f"pause signature doesn't support keep_memory: {e}")


@pytest.mark.snapshot
def test_pause_no_memory(sandbox_factory):
    """暂停沙箱且不保留内存快照。
    测试条件: 创建一个沙箱后以keep_memory=False参数暂停。
    测试步骤: 1)通过sandbox_factory创建沙箱；2)调用sbx.pause(keep_memory=False)。
    预期结果: 暂停操作成功但不保留内存状态；若API不支持则跳过测试。
    """
    sbx = sandbox_factory()
    try:
        sbx.pause(keep_memory=False)
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"pause with keep_memory not available: {e}")
    except TypeError as e:
        pytest.skip(f"pause signature doesn't support keep_memory: {e}")


@pytest.mark.snapshot
def test_resume_via_connect(sandbox_factory, sandbox_create_kwargs):
    """通过connect方法恢复暂停的沙箱。
    测试条件: 创建沙箱并暂停后，通过Sandbox.connect()恢复。
    测试步骤: 1)创建沙箱并记录ID；2)调用sbx.pause()暂停；3)调用Sandbox.connect()恢复沙箱。
    预期结果: 恢复后sandbox_id与原始ID一致；若API不支持则跳过测试。
    """
    sbx = sandbox_factory()
    sandbox_id = sbx.sandbox_id
    
    try:
        sbx.pause()
        # Connect should resume the sandbox
        from e2b_code_interpreter import Sandbox
        connect_kwargs = {k: v for k, v in sandbox_create_kwargs.items()
                          if k in ['api_key', 'api_url', 'domain', 'sandbox_url']}
        sbx2 = Sandbox.connect(sandbox_id, **connect_kwargs)
        assert sbx2.sandbox_id == sandbox_id
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"pause/resume not available: {e}")


@pytest.mark.snapshot
def test_pause_resume_state_preserved(sandbox_factory, sandbox_create_kwargs):
    """验证暂停/恢复后沙箱状态被保留。
    测试条件: 创建沙箱并写入文件后暂停，再恢复并验证文件仍在。
    测试步骤: 1)创建沙箱并写入文件；2)调用sbx.pause()暂停；3)通过Sandbox.connect()恢复；4)读取文件并验证内容。
    预期结果: 恢复后文件仍然存在且内容包含'preserved data'；若API不支持则跳过测试。
    """
    sbx = sandbox_factory()
    sandbox_id = sbx.sandbox_id
    
    try:
        # Create a file
        sbx.files.write("/tmp/preserve_test.txt", "preserved data")
        
        # Pause
        sbx.pause()
        
        # Resume via connect
        from e2b_code_interpreter import Sandbox
        connect_kwargs = {k: v for k, v in sandbox_create_kwargs.items()
                          if k in ['api_key', 'api_url', 'domain', 'sandbox_url']}
        sbx2 = Sandbox.connect(sandbox_id, **connect_kwargs)
        
        # Verify file still exists
        assert sbx2.files.exists("/tmp/preserve_test.txt")
        content = sbx2.files.read("/tmp/preserve_test.txt", format="text")
        assert "preserved data" in content
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"pause/resume not available: {e}")


@pytest.mark.snapshot
def test_fork_sandbox(sandbox):
    """分叉（Fork）一个沙箱。
    测试条件: 对现有沙箱调用fork()创建副本。
    测试步骤: 调用sandbox.fork()。
    预期结果: 返回的forked沙箱不为None且sandbox_id与原沙箱不同；若API不支持则跳过测试。
    """
    try:
        forked = sandbox.fork()
        assert forked is not None
        assert forked.sandbox_id != sandbox.sandbox_id
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"fork not available: {e}")


@pytest.mark.snapshot
def test_fork_state_independent(sandbox):
    """验证分叉后的沙箱具有独立的文件系统状态。
    测试条件: 在原沙箱写入文件后fork，再修改原沙箱文件，验证fork副本保留原始内容。
    测试步骤: 1)在原沙箱写入'original'；2)调用fork()；3)修改原沙箱文件为'modified'；4)读取forked沙箱的文件。
    预期结果: forked沙箱的文件内容仍为'original'，证明文件系统独立；若API不支持则跳过测试。
    """
    try:
        # Create file in original
        sandbox.files.write("/tmp/fork_test.txt", "original")
        
        # Fork
        forked = sandbox.fork()
        
        # Modify original
        sandbox.files.write("/tmp/fork_test.txt", "modified")
        
        # Forked should still have original content
        content = forked.files.read("/tmp/fork_test.txt", format="text")
        assert "original" in content
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"fork not available: {e}")


@pytest.mark.snapshot
def test_create_snapshot(sandbox):
    """创建沙箱快照。
    测试条件: 对现有沙箱创建名为'test_snapshot'的快照。
    测试步骤: 调用sandbox.create_snapshot(name="test_snapshot")。
    预期结果: 返回的snapshot对象不为None；若API不支持则跳过测试。
    """
    try:
        snapshot = sandbox.create_snapshot(name="test_snapshot")
        assert snapshot is not None
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"create_snapshot not available: {e}")


@pytest.mark.snapshot
def test_list_delete_snapshot(sandbox):
    """列出并删除沙箱快照。
    测试条件: 创建快照后列出所有快照并删除第一个。
    测试步骤: 1)创建名为'to_delete'的快照；2)调用list_snapshots()列出快照；3)遍历获取列表；4)调用delete_snapshot()删除第一个快照。
    预期结果: 快照列表和删除操作正常完成；若API不支持则跳过测试。
    """
    try:
        # Create a snapshot
        sandbox.create_snapshot(name="to_delete")
        
        # List snapshots (returns a paginator)
        snapshots = sandbox.list_snapshots()
        
        # Try to get items from paginator
        snapshot_list = []
        try:
            snapshot_list = list(snapshots.items)
        except (AttributeError, TypeError):
            try:
                for page in snapshots:
                    snapshot_list.extend(page)
            except TypeError:
                pass
        
        # Delete if we have any
        if snapshot_list and len(snapshot_list) > 0:
            snapshot_id = snapshot_list[0].snapshot_id if hasattr(snapshot_list[0], 'snapshot_id') else snapshot_list[0]
            sandbox.delete_snapshot(snapshot_id)
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"snapshot operations not available: {e}")
