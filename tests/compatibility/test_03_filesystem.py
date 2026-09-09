"""
文件系统测试：读、写、列表、存在性检查、重命名、删除、监听。
"""
import pytest
import time


@pytest.mark.filesystem
def test_write_read_text(sandbox):
    """写入并读取文本文件。
    测试条件: 向/tmp/test.txt写入文本内容'Hello, E2B!'。
    测试步骤: 1)调用files.write()写入文本；2)调用files.read(format="text")读取内容。
    预期结果: 读取的文本内容包含写入的'Hello, E2B!'字符串。
    """
    content = "Hello, E2B!"
    sandbox.files.write("/tmp/test.txt", content)
    result = sandbox.files.read("/tmp/test.txt", format="text")
    assert content in result


@pytest.mark.filesystem
def test_write_read_bytes(sandbox):
    """写入并读取二进制文件。
    测试条件: 向/tmp/test.bin写入字节数据b'\\x00\\x01\\x02\\x03\\x04'。
    测试步骤: 1)调用files.write()写入bytes；2)调用files.read(format="bytes")读取内容。
    预期结果: 读取的字节数据与写入的完全一致。
    """
    content = b"\x00\x01\x02\x03\x04"
    sandbox.files.write("/tmp/test.bin", content)
    result = sandbox.files.read("/tmp/test.bin", format="bytes")
    assert result == content


@pytest.mark.filesystem
def test_write_files_batch(sandbox):
    """批量写入多个文件。
    测试条件: 准备3个文件的路径和数据列表。
    测试步骤: 1)调用files.write_files()批量写入；2)逐个调用files.exists()验证文件存在。
    预期结果: 所有3个文件均成功创建并通过存在性检查。
    """
    files = [
        {"path": "/tmp/file1.txt", "data": "content1"},
        {"path": "/tmp/file2.txt", "data": "content2"},
        {"path": "/tmp/file3.txt", "data": "content3"},
    ]
    sandbox.files.write_files(files)
    
    # Verify all files exist
    for f in files:
        assert sandbox.files.exists(f["path"])


@pytest.mark.filesystem
def test_list_directory(sandbox):
    """列出目录内容。
    测试条件: 在/tmp/list_test目录下创建2个文件。
    测试步骤: 1)写入file1.txt和file2.txt；2)调用files.list()列出目录。
    预期结果: 返回的条目列表不为None且至少包含2个条目。
    """
    # Create some files
    sandbox.files.write("/tmp/list_test/file1.txt", "test")
    sandbox.files.write("/tmp/list_test/file2.txt", "test")
    
    # List the directory
    entries = sandbox.files.list("/tmp/list_test")
    assert entries is not None
    assert len(entries) >= 2


@pytest.mark.filesystem
def test_exists_true(sandbox):
    """验证exists()对已存在的文件返回True。
    测试条件: 先向/tmp/exists_test.txt写入文件。
    测试步骤: 1)调用files.write()创建文件；2)调用files.exists()检查文件是否存在。
    预期结果: files.exists()返回True。
    """
    sandbox.files.write("/tmp/exists_test.txt", "test")
    assert sandbox.files.exists("/tmp/exists_test.txt") is True


@pytest.mark.filesystem
def test_exists_false(sandbox):
    """验证exists()对不存在的文件返回False。
    测试条件: 查询一个从未创建过的文件路径。
    测试步骤: 调用files.exists("/tmp/nonexistent_file_xyz123.txt")。
    预期结果: files.exists()返回False。
    """
    assert sandbox.files.exists("/tmp/nonexistent_file_xyz123.txt") is False


@pytest.mark.filesystem
def test_get_info_file(sandbox):
    """获取文件信息。
    测试条件: 先向/tmp/info_test.txt写入文件内容。
    测试步骤: 1)调用files.write()创建文件；2)调用files.get_info()获取文件信息。
    预期结果: 返回的info对象不为None。
    """
    sandbox.files.write("/tmp/info_test.txt", "test content")
    info = sandbox.files.get_info("/tmp/info_test.txt")
    assert info is not None


@pytest.mark.filesystem
def test_make_dir(sandbox):
    """创建目录。
    测试条件: 在沙箱中创建/tmp/new_directory目录。
    测试步骤: 1)调用files.make_dir()创建目录；2)调用files.exists()验证目录存在。
    预期结果: files.exists()返回True，目录创建成功。
    """
    sandbox.files.make_dir("/tmp/new_directory")
    assert sandbox.files.exists("/tmp/new_directory")


@pytest.mark.filesystem
def test_rename(sandbox):
    """重命名文件。
    测试条件: 先创建/tmp/old_name.txt文件，然后将其重命名为/tmp/new_name.txt。
    测试步骤: 1)写入old_name.txt；2)调用files.rename()重命名；3)验证新文件存在且旧文件不存在。
    预期结果: new_name.txt存在，old_name.txt不存在。
    """
    sandbox.files.write("/tmp/old_name.txt", "test")
    sandbox.files.rename("/tmp/old_name.txt", "/tmp/new_name.txt")
    assert sandbox.files.exists("/tmp/new_name.txt")
    assert not sandbox.files.exists("/tmp/old_name.txt")


@pytest.mark.filesystem
def test_remove_file(sandbox):
    """删除文件。
    测试条件: 先创建/tmp/to_remove.txt文件，然后将其删除。
    测试步骤: 1)写入to_remove.txt；2)调用files.remove()删除文件；3)调用files.exists()验证文件不存在。
    预期结果: files.exists()返回False，文件已成功删除。
    """
    sandbox.files.write("/tmp/to_remove.txt", "test")
    sandbox.files.remove("/tmp/to_remove.txt")
    assert not sandbox.files.exists("/tmp/to_remove.txt")


@pytest.mark.filesystem
def test_remove_directory(sandbox):
    """删除目录。
    测试条件: 创建/tmp/dir_to_remove目录并在其中写入文件，然后删除整个目录。
    测试步骤: 1)创建目录并写入文件；2)调用files.remove()删除目录；3)验证目录不存在。
    预期结果: files.exists()返回False，目录及其内容已被成功删除。
    """
    sandbox.files.make_dir("/tmp/dir_to_remove")
    sandbox.files.write("/tmp/dir_to_remove/file.txt", "test")
    sandbox.files.remove("/tmp/dir_to_remove")
    assert not sandbox.files.exists("/tmp/dir_to_remove")


@pytest.mark.filesystem
def test_read_nonexistent(sandbox):
    """读取不存在的文件应抛出异常。
    测试条件: 尝试读取一个从未创建过的文件路径。
    测试步骤: 调用files.read("/tmp/definitely_not_exists_xyz.txt")。
    预期结果: 抛出FileNotFoundException或类似异常。
    """
    try:
        sandbox.files.read("/tmp/definitely_not_exists_xyz.txt")
        pytest.fail("Should have raised an exception")
    except Exception as e:
        # Expected: FileNotFoundException or similar
        assert True


@pytest.mark.filesystem
def test_large_file(sandbox):
    """写入并读取大文件（1MB）。
    测试条件: 生成1MB的文本数据（1048576个'x'字符）。
    测试步骤: 1)调用files.write()写入1MB数据；2)调用files.read(format="text")读取内容。
    预期结果: 读取内容的长度与写入数据长度完全一致。
    """
    # Create 1MB of data
    content = "x" * (1024 * 1024)
    sandbox.files.write("/tmp/large_file.txt", content)
    result = sandbox.files.read("/tmp/large_file.txt", format="text")
    assert len(result) == len(content)


@pytest.mark.filesystem
def test_watch_dir(sandbox):
    """监听目录变化。
    测试条件: 在/tmp/watch_test目录中设置监听，然后创建新文件触发事件。
    测试步骤: 1)创建目录；2)调用files.watch_dir()启动监听；3)写入新文件；4)等待0.5秒后获取事件；5)停止监听。
    预期结果: watch_handle可正常创建和停止；若API不支持则跳过测试。
    """
    sandbox.files.make_dir("/tmp/watch_test")
    
    try:
        watch_handle = sandbox.files.watch_dir("/tmp/watch_test")
        
        # Create a file to trigger event
        sandbox.files.write("/tmp/watch_test/new_file.txt", "test")
        time.sleep(0.5)
        
        # Get events
        events = watch_handle.get_new_events()
        # Events might be empty or have entries depending on timing
        
        watch_handle.stop()
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"watch_dir not available: {e}")


@pytest.mark.filesystem
def test_watch_handle_stop(sandbox):
    """停止目录监听。
    测试条件: 在/tmp/watch_stop_test目录中启动监听后立即停止。
    测试步骤: 1)创建目录；2)调用files.watch_dir()启动监听；3)调用watch_handle.stop()停止监听。
    预期结果: stop()调用成功；若API不支持则跳过测试。
    """
    sandbox.files.make_dir("/tmp/watch_stop_test")
    
    try:
        watch_handle = sandbox.files.watch_dir("/tmp/watch_stop_test")
        watch_handle.stop()
    except (AttributeError, NotImplementedError) as e:
        pytest.skip(f"watch_dir not available: {e}")
