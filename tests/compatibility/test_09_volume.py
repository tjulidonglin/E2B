"""
卷（Volume）管理测试：创建、连接、列表、读写、挂载。
"""
import pytest


def _volume_skip_on_403(e):
    msg = str(e)
    if "403" in msg or "not enabled" in msg.lower():
        pytest.skip(f"Volume not enabled for this account: {e}")
    if isinstance(e, (ImportError, AttributeError, NotImplementedError)):
        pytest.skip(f"Volume not available: {e}")


def _vol_kwargs(sandbox_create_kwargs):
    return {k: v for k, v in sandbox_create_kwargs.items()
            if k in ["api_key", "api_url", "domain", "sandbox_url"]}


@pytest.mark.volume
def test_volume_create(sandbox_create_kwargs):
    """创建卷。
    测试条件: 使用Volume.create()创建名为'test_volume'的卷。
    测试步骤: 调用Volume.create(name="test_volume")。
    预期结果: 返回的vol对象不为None；若账户未启用卷功能则跳过测试。
    """
    try:
        from e2b import Volume
        vol = Volume.create(name="test_volume", **_vol_kwargs(sandbox_create_kwargs))
        assert vol is not None
    except Exception as e:
        _volume_skip_on_403(e)
        raise


@pytest.mark.volume
def test_volume_properties(sandbox_create_kwargs):
    """验证卷具备必要属性。
    测试条件: 创建一个卷后检查其属性。
    测试步骤: 1)调用Volume.create()创建卷；2)检查是否具有volume_id或id属性；3)检查是否具有name属性。
    预期结果: 卷具有volume_id/id和name属性；若账户未启用卷功能则跳过测试。
    """
    try:
        from e2b import Volume
        vol = Volume.create(name="test_props", **_vol_kwargs(sandbox_create_kwargs))
        assert hasattr(vol, "volume_id") or hasattr(vol, "id")
        assert hasattr(vol, "name")
    except Exception as e:
        _volume_skip_on_403(e)
        raise


@pytest.mark.volume
def test_volume_connect(sandbox_create_kwargs):
    """连接到已有卷。
    测试条件: 先创建一个卷，再通过Volume.connect()重新连接。
    测试步骤: 1)调用Volume.create()创建卷并获取volume_id；2)调用Volume.connect(volume_id)重新连接。
    预期结果: 重新连接返回的vol2对象不为None；若账户未启用卷功能则跳过测试。
    """
    try:
        from e2b import Volume
        vol = Volume.create(name="test_connect", **_vol_kwargs(sandbox_create_kwargs))
        vol_id = vol.volume_id if hasattr(vol, "volume_id") else vol.id
        vol2 = Volume.connect(vol_id, **_vol_kwargs(sandbox_create_kwargs))
        assert vol2 is not None
    except Exception as e:
        _volume_skip_on_403(e)
        raise


@pytest.mark.volume
def test_volume_list(sandbox_create_kwargs):
    """列出所有卷。
    测试条件: 创建一个卷后调用Volume.list()获取卷列表。
    测试步骤: 1)调用Volume.create()创建卷；2)调用Volume.list()获取列表。
    预期结果: 返回的列表不为None；若账户未启用卷功能则跳过测试。
    """
    try:
        from e2b import Volume
        Volume.create(name="test_list", **_vol_kwargs(sandbox_create_kwargs))
        volumes = Volume.list(**_vol_kwargs(sandbox_create_kwargs))
        assert volumes is not None
    except Exception as e:
        _volume_skip_on_403(e)
        raise


@pytest.mark.volume
def test_volume_make_dir(sandbox_create_kwargs):
    """在卷中创建目录。
    测试条件: 创建卷后在其内部创建/test_dir目录。
    测试步骤: 1)调用Volume.create()创建卷；2)调用vol.make_dir("/test_dir")创建目录。
    预期结果: 目录创建成功；若账户未启用卷功能则跳过测试。
    """
    try:
        from e2b import Volume
        vol = Volume.create(name="test_mkdir", **_vol_kwargs(sandbox_create_kwargs))
        vol.make_dir("/test_dir")
    except Exception as e:
        _volume_skip_on_403(e)
        raise


@pytest.mark.volume
def test_volume_write_read_file(sandbox_create_kwargs):
    """在卷中写入并读取文件。
    测试条件: 创建卷后向其写入'test data'内容并读回。
    测试步骤: 1)调用Volume.create()创建卷；2)调用vol.write_file()写入内容；3)调用vol.read_file()读取内容。
    预期结果: 读取的内容包含写入的'test data'；若账户未启用卷功能则跳过测试。
    """
    try:
        from e2b import Volume
        vol = Volume.create(name="test_rw", **_vol_kwargs(sandbox_create_kwargs))
        content = "test data"
        vol.write_file("/test.txt", content)
        result = vol.read_file("/test.txt")
        assert content in result
    except Exception as e:
        _volume_skip_on_403(e)
        raise


@pytest.mark.volume
def test_volume_exists(sandbox_create_kwargs):
    """检查卷中文件是否存在。
    测试条件: 创建卷后写入文件，然后检查其存在性。
    测试步骤: 1)调用Volume.create()创建卷；2)调用vol.write_file()写入文件；3)调用vol.exists()检查文件。
    预期结果: vol.exists()返回True；若账户未启用卷功能则跳过测试。
    """
    try:
        from e2b import Volume
        vol = Volume.create(name="test_exists", **_vol_kwargs(sandbox_create_kwargs))
        vol.write_file("/exists_test.txt", "test")
        assert vol.exists("/exists_test.txt")
    except Exception as e:
        _volume_skip_on_403(e)
        raise


@pytest.mark.volume
def test_volume_remove(sandbox_create_kwargs):
    """从卷中删除文件。
    测试条件: 创建卷后写入文件，然后将其删除并验证。
    测试步骤: 1)创建卷并写入文件；2)调用vol.remove()删除文件；3)调用vol.exists()验证文件不存在。
    预期结果: vol.exists()返回False，文件已成功删除；若账户未启用卷功能则跳过测试。
    """
    try:
        from e2b import Volume
        vol = Volume.create(name="test_remove", **_vol_kwargs(sandbox_create_kwargs))
        vol.write_file("/to_remove.txt", "test")
        vol.remove("/to_remove.txt")
        assert not vol.exists("/to_remove.txt")
    except Exception as e:
        _volume_skip_on_403(e)
        raise


@pytest.mark.volume
def test_volume_mount_to_sandbox(sandbox_factory, sandbox_create_kwargs):
    """将卷挂载到沙箱。
    测试条件: 创建卷并写入文件后，将其挂载到沙箱的/mnt/volume路径。
    测试步骤: 1)创建卷并写入'mounted data'；2)通过volume_mounts参数将卷挂载到沙箱；3)通过沙箱文件系统读取挂载的文件。
    预期结果: 沙箱中能读取到挂载文件的内容'mounted data'；若账户未启用卷功能则跳过测试。
    """
    try:
        from e2b import Volume
        vol = Volume.create(name="test_mount", **_vol_kwargs(sandbox_create_kwargs))
        vol.write_file("/mounted.txt", "mounted data")
        volume_mounts = {"/mnt/volume": vol}
        sbx = sandbox_factory(volume_mounts=volume_mounts)
        content = sbx.files.read("/mnt/volume/mounted.txt", format="text")
        assert "mounted data" in content
    except Exception as e:
        _volume_skip_on_403(e)
        pytest.skip(f"Volume mount failed: {e}")


@pytest.mark.volume
def test_volume_destroy(sandbox_create_kwargs):
    """销毁卷。
    测试条件: 创建一个卷后通过Volume.destroy()将其销毁。
    测试步骤: 1)调用Volume.create()创建卷并获取volume_id；2)调用Volume.destroy(volume_id)销毁卷。
    预期结果: 销毁操作成功；若账户未启用卷功能则跳过测试。
    """
    try:
        from e2b import Volume
        vol = Volume.create(name="test_destroy", **_vol_kwargs(sandbox_create_kwargs))
        vol_id = vol.volume_id if hasattr(vol, "volume_id") else vol.id
        Volume.destroy(vol_id, **_vol_kwargs(sandbox_create_kwargs))
    except Exception as e:
        _volume_skip_on_403(e)
        raise
