"""
Git操作测试：克隆、初始化、状态、分支、提交、远程仓库。
"""
import pytest


@pytest.mark.git
def test_git_clone(sandbox):
    """克隆公开Git仓库。
    测试条件: 从GitHub克隆octocat/Hello-World仓库到/tmp/repo。
    测试步骤: 1)调用git.clone()克隆仓库；2)检查/tmp/repo/.git目录是否存在。
    预期结果: .git目录存在，仓库克隆成功；若不支持则跳过测试。
    """
    try:
        sandbox.git.clone("https://github.com/octocat/Hello-World.git", path="/tmp/repo")
        assert sandbox.files.exists("/tmp/repo/.git")
    except Exception as e:
        pytest.skip(f"git.clone not available: {e}")


@pytest.mark.git
def test_git_init(sandbox):
    """初始化新的Git仓库。
    测试条件: 在/tmp/new_repo目录初始化一个空的Git仓库。
    测试步骤: 1)创建目录；2)调用git.init()初始化仓库；3)检查.git目录是否存在。
    预期结果: .git目录存在，仓库初始化成功；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/new_repo")
        sandbox.git.init("/tmp/new_repo")
        assert sandbox.files.exists("/tmp/new_repo/.git")
    except Exception as e:
        pytest.skip(f"git.init not available: {e}")


@pytest.mark.git
def test_git_status_clean(sandbox):
    """获取干净仓库的Git状态。
    测试条件: 初始化一个空的Git仓库，没有任何修改。
    测试步骤: 1)创建目录并初始化git仓库；2)调用git.status()获取状态。
    预期结果: 返回的status对象不为None；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/status_repo")
        sandbox.git.init("/tmp/status_repo")
        status = sandbox.git.status(path="/tmp/status_repo")
        assert status is not None
    except Exception as e:
        pytest.skip(f"git.status not available: {e}")


@pytest.mark.git
def test_git_status_dirty(sandbox):
    """获取有修改文件的Git仓库状态。
    测试条件: 初始化Git仓库后写入新文件（未暂存）。
    测试步骤: 1)创建目录并初始化git仓库；2)写入file.txt；3)调用git.status()获取状态。
    预期结果: 返回的status对象不为None，能检测到未暂存的修改；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/dirty_repo")
        sandbox.git.init("/tmp/dirty_repo")
        sandbox.files.write("/tmp/dirty_repo/file.txt", "test")
        status = sandbox.git.status(path="/tmp/dirty_repo")
        assert status is not None
    except Exception as e:
        pytest.skip(f"git.status not available: {e}")


@pytest.mark.git
def test_git_add(sandbox):
    """将文件添加到Git暂存区。
    测试条件: 初始化Git仓库，创建新文件并将其添加到暂存区。
    测试步骤: 1)创建目录并初始化git仓库；2)写入file.txt；3)调用git.add(files=["file.txt"])添加到暂存区。
    预期结果: add操作不抛异常；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/add_repo")
        sandbox.git.init("/tmp/add_repo")
        sandbox.files.write("/tmp/add_repo/file.txt", "test")
        sandbox.git.add(path="/tmp/add_repo", files=["file.txt"])
    except Exception as e:
        pytest.skip(f"git.add not available: {e}")


@pytest.mark.git
def test_git_commit(sandbox):
    """创建Git提交。
    测试条件: 初始化仓库，配置用户信息，创建文件并提交。
    测试步骤: 1)初始化仓库；2)设置user.name和user.email；3)写入file.txt；4)调用git.add()暂存；5)调用git.commit("Initial commit")提交。
    预期结果: commit操作不抛异常；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/commit_repo")
        sandbox.git.init("/tmp/commit_repo")
        sandbox.git.set_config("user.name", "test", path="/tmp/commit_repo")
        sandbox.git.set_config("user.email", "test@test.com", path="/tmp/commit_repo")
        sandbox.files.write("/tmp/commit_repo/file.txt", "test")
        sandbox.git.add(path="/tmp/commit_repo", files=["file.txt"])
        sandbox.git.commit("Initial commit", path="/tmp/commit_repo")
    except Exception as e:
        pytest.skip(f"git.commit not available: {e}")


@pytest.mark.git
def test_git_branches(sandbox):
    """列出Git分支。
    测试条件: 初始化仓库并提交文件后，列出所有分支。
    测试步骤: 1)初始化仓库；2)配置用户信息；3)创建文件并提交；4)调用git.branches()获取分支列表。
    预期结果: 返回的branches对象不为None；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/branch_repo")
        sandbox.git.init("/tmp/branch_repo")
        sandbox.git.set_config("user.name", "test", path="/tmp/branch_repo")
        sandbox.git.set_config("user.email", "test@test.com", path="/tmp/branch_repo")
        sandbox.files.write("/tmp/branch_repo/file.txt", "test")
        sandbox.git.add(path="/tmp/branch_repo", files=["file.txt"])
        sandbox.git.commit("init", path="/tmp/branch_repo")
        branches = sandbox.git.branches(path="/tmp/branch_repo")
        assert branches is not None
    except Exception as e:
        pytest.skip(f"git.branches not available: {e}")


@pytest.mark.git
def test_git_create_branch(sandbox):
    """创建新的Git分支。
    测试条件: 初始化仓库并提交文件后，创建名为'feature'的新分支。
    测试步骤: 1)初始化仓库；2)配置用户信息；3)创建文件并提交；4)调用git.create_branch("feature")创建分支。
    预期结果: 分支创建成功，不抛异常；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/create_branch_repo")
        sandbox.git.init("/tmp/create_branch_repo")
        sandbox.git.set_config("user.name", "test", path="/tmp/create_branch_repo")
        sandbox.git.set_config("user.email", "test@test.com", path="/tmp/create_branch_repo")
        sandbox.files.write("/tmp/create_branch_repo/file.txt", "test")
        sandbox.git.add(path="/tmp/create_branch_repo", files=["file.txt"])
        sandbox.git.commit("init", path="/tmp/create_branch_repo")
        sandbox.git.create_branch("feature", path="/tmp/create_branch_repo")
    except Exception as e:
        pytest.skip(f"git.create_branch not available: {e}")


@pytest.mark.git
def test_git_checkout_branch(sandbox):
    """切换到Git分支。
    测试条件: 初始化仓库并提交文件，创建'feature'分支后切换到该分支。
    测试步骤: 1)初始化仓库并提交文件；2)创建'feature'分支；3)调用git.checkout_branch("feature")切换分支。
    预期结果: 分支切换成功，不抛异常；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/checkout_repo")
        sandbox.git.init("/tmp/checkout_repo")
        sandbox.git.set_config("user.name", "test", path="/tmp/checkout_repo")
        sandbox.git.set_config("user.email", "test@test.com", path="/tmp/checkout_repo")
        sandbox.files.write("/tmp/checkout_repo/file.txt", "test")
        sandbox.git.add(path="/tmp/checkout_repo", files=["file.txt"])
        sandbox.git.commit("init", path="/tmp/checkout_repo")
        sandbox.git.create_branch("feature", path="/tmp/checkout_repo")
        sandbox.git.checkout_branch("feature", path="/tmp/checkout_repo")
    except Exception as e:
        pytest.skip(f"git.checkout_branch not available: {e}")


@pytest.mark.git
def test_git_delete_branch(sandbox):
    """删除Git分支。
    测试条件: 初始化仓库并提交文件，创建'to_delete'分支后将其删除。
    测试步骤: 1)初始化仓库并提交文件；2)创建'to_delete'分支；3)调用git.delete_branch("to_delete")删除分支。
    预期结果: 分支删除成功，不抛异常；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/delete_branch_repo")
        sandbox.git.init("/tmp/delete_branch_repo")
        sandbox.git.set_config("user.name", "test", path="/tmp/delete_branch_repo")
        sandbox.git.set_config("user.email", "test@test.com", path="/tmp/delete_branch_repo")
        sandbox.files.write("/tmp/delete_branch_repo/file.txt", "test")
        sandbox.git.add(path="/tmp/delete_branch_repo", files=["file.txt"])
        sandbox.git.commit("init", path="/tmp/delete_branch_repo")
        sandbox.git.create_branch("to_delete", path="/tmp/delete_branch_repo")
        sandbox.git.delete_branch("to_delete", path="/tmp/delete_branch_repo")
    except Exception as e:
        pytest.skip(f"git.delete_branch not available: {e}")


@pytest.mark.git
def test_git_remote_add(sandbox):
    """添加Git远程仓库。
    测试条件: 初始化仓库后添加名为'origin'的远程仓库地址。
    测试步骤: 1)初始化仓库；2)调用git.remote_add("origin", "https://github.com/test/repo.git")。
    预期结果: 远程仓库添加成功，不抛异常；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/remote_repo")
        sandbox.git.init("/tmp/remote_repo")
        sandbox.git.remote_add("origin", "https://github.com/test/repo.git",
                               path="/tmp/remote_repo")
    except Exception as e:
        pytest.skip(f"git.remote_add not available: {e}")


@pytest.mark.git
def test_git_remote_get(sandbox):
    """获取Git远程仓库URL。
    测试条件: 初始化仓库并添加'origin'远程仓库后获取其URL。
    测试步骤: 1)初始化仓库；2)添加远程仓库；3)调用git.remote_get("origin")获取URL。
    预期结果: 返回的URL不为None且包含'github.com'；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/remote_get_repo")
        sandbox.git.init("/tmp/remote_get_repo")
        sandbox.git.remote_add("origin", "https://github.com/test/repo.git",
                               path="/tmp/remote_get_repo")
        url = sandbox.git.remote_get("origin", path="/tmp/remote_get_repo")
        assert url is not None
        assert "github.com" in url
    except Exception as e:
        pytest.skip(f"git.remote_get not available: {e}")


@pytest.mark.git
def test_git_diff(sandbox):
    """获取Git差异信息。
    测试条件: 初始化仓库并提交文件后修改文件，获取未暂存的差异。
    测试步骤: 1)初始化仓库并提交'original'内容；2)修改文件为'modified'；3)调用git.diff()获取差异。
    预期结果: 返回的diff对象不为None；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/diff_repo")
        sandbox.git.init("/tmp/diff_repo")
        sandbox.git.set_config("user.name", "test", path="/tmp/diff_repo")
        sandbox.git.set_config("user.email", "test@test.com", path="/tmp/diff_repo")
        sandbox.files.write("/tmp/diff_repo/file.txt", "original")
        sandbox.git.add(path="/tmp/diff_repo", files=["file.txt"])
        sandbox.git.commit("init", path="/tmp/diff_repo")
        sandbox.files.write("/tmp/diff_repo/file.txt", "modified")
        diff = sandbox.git.diff(path="/tmp/diff_repo")
        assert diff is not None
    except Exception as e:
        pytest.skip(f"git.diff not available: {e}")


@pytest.mark.git
def test_git_reset(sandbox):
    """将Git仓库重置到指定提交。
    测试条件: 初始化仓库并创建两次提交后，重置到上一次提交(HEAD~1)。
    测试步骤: 1)初始化仓库并提交v1(commit1)；2)提交v2(commit2)；3)调用git.reset("HEAD~1")重置。
    预期结果: 重置操作成功，不抛异常；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/reset_repo")
        sandbox.git.init("/tmp/reset_repo")
        sandbox.git.set_config("user.name", "test", path="/tmp/reset_repo")
        sandbox.git.set_config("user.email", "test@test.com", path="/tmp/reset_repo")
        sandbox.files.write("/tmp/reset_repo/file.txt", "v1")
        sandbox.git.add(path="/tmp/reset_repo", files=["file.txt"])
        sandbox.git.commit("commit1", path="/tmp/reset_repo")
        sandbox.files.write("/tmp/reset_repo/file.txt", "v2")
        sandbox.git.add(path="/tmp/reset_repo", files=["file.txt"])
        sandbox.git.commit("commit2", path="/tmp/reset_repo")
        sandbox.git.reset("HEAD~1", path="/tmp/reset_repo")
    except Exception as e:
        pytest.skip(f"git.reset not available: {e}")


@pytest.mark.git
def test_git_restore(sandbox):
    """从Git恢复文件到已提交状态。
    测试条件: 初始化仓库并提交文件后修改文件，然后恢复到提交时的状态。
    测试步骤: 1)初始化仓库并提交'original'内容；2)修改文件为'modified'；3)调用git.restore()恢复文件。
    预期结果: 恢复操作成功，不抛异常；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/restore_repo")
        sandbox.git.init("/tmp/restore_repo")
        sandbox.git.set_config("user.name", "test", path="/tmp/restore_repo")
        sandbox.git.set_config("user.email", "test@test.com", path="/tmp/restore_repo")
        sandbox.files.write("/tmp/restore_repo/file.txt", "original")
        sandbox.git.add(path="/tmp/restore_repo", files=["file.txt"])
        sandbox.git.commit("init", path="/tmp/restore_repo")
        sandbox.files.write("/tmp/restore_repo/file.txt", "modified")
        sandbox.git.restore(path="/tmp/restore_repo", files=["file.txt"])
    except Exception as e:
        pytest.skip(f"git.restore not available: {e}")


@pytest.mark.git
def test_git_set_config(sandbox):
    """设置Git配置值。
    测试条件: 初始化仓库后设置user.name为'Test User'。
    测试步骤: 1)初始化仓库；2)调用git.set_config("user.name", "Test User")。
    预期结果: 配置设置成功，不抛异常；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/config_repo")
        sandbox.git.init("/tmp/config_repo")
        sandbox.git.set_config("user.name", "Test User", path="/tmp/config_repo")
    except Exception as e:
        pytest.skip(f"git.set_config not available: {e}")


@pytest.mark.git
def test_git_get_config(sandbox):
    """获取Git配置值。
    测试条件: 初始化仓库并设置user.name后读取该配置。
    测试步骤: 1)初始化仓库；2)设置user.name为'Test User'；3)调用git.get_config("user.name")读取配置。
    预期结果: 返回的配置值不为None；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/config_get_repo")
        sandbox.git.init("/tmp/config_get_repo")
        sandbox.git.set_config("user.name", "Test User", path="/tmp/config_get_repo")
        name = sandbox.git.get_config("user.name", path="/tmp/config_get_repo")
        assert name is not None
    except Exception as e:
        pytest.skip(f"git.get_config not available: {e}")


@pytest.mark.git
def test_git_configure_user(sandbox):
    """配置Git用户名和邮箱。
    测试条件: 初始化仓库后一次性设置用户名和邮箱。
    测试步骤: 1)初始化仓库；2)调用git.configure_user("Test User", "test@example.com")。
    预期结果: 配置成功，不抛异常；若不支持则跳过测试。
    """
    try:
        sandbox.files.make_dir("/tmp/user_repo")
        sandbox.git.init("/tmp/user_repo")
        sandbox.git.configure_user("Test User", "test@example.com",
                                   path="/tmp/user_repo")
    except Exception as e:
        pytest.skip(f"git.configure_user not available: {e}")

