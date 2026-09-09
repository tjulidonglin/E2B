"""
conftest.py - Shared fixtures for E2B API compatibility tests.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))
sys.path.insert(0, str(PROJECT_ROOT / "tests" / "compatibility"))

from e2b_code_interpreter import Sandbox
from report_collector import HTMLReportCollector

# Huawei Cloud patch (optional)
try:
    from utils.huawei_patch import patch_sandbox_if_needed, safe_kill_sandbox
except ImportError:
    def patch_sandbox_if_needed(sbx):
        return sbx
    def safe_kill_sandbox(sbx, sandbox_id=None):
        try:
            sbx.kill()
        except Exception:
            pass


def detect_platform() -> Dict[str, str]:
    api_url = os.environ.get("E2B_API_URL", "")
    sandbox_url = os.environ.get("E2B_SANDBOX_URL", "")
    domain = os.environ.get("E2B_DOMAIN", "")
    combined = f"{api_url} {sandbox_url} {domain}".lower()

    if "huaweicloud" in combined or "agentsphere" in combined:
        name = "huawei"
    elif "tencent" in combined or "cube" in combined:
        name = "tencent"
    elif "e2b.dev" in combined or not api_url:
        name = "official"
    else:
        name = "custom"

    return {
        "name": name,
        "api_url": api_url or "(default: api.e2b.dev)",
        "sandbox_url": sandbox_url or "(not set)",
        "domain": domain or "(not set)",
        "template": os.environ.get("CUBE_TEMPLATE_ID", "base"),
    }


_report_collector = HTMLReportCollector()


@pytest.fixture(scope="session")
def platform_info():
    info = detect_platform()
    _report_collector.set_platform(info)
    return info


@pytest.fixture(scope="session")
def sandbox_create_kwargs(platform_info):
    kwargs: Dict[str, Any] = {
        "template": platform_info["template"] if platform_info["template"] != "base" else "code-interpreter-v1",
        "timeout": 120,
    }
    for env_key, kwarg_key in [
        ("E2B_API_KEY", "api_key"),
        ("E2B_API_URL", "api_url"),
        ("E2B_SANDBOX_URL", "sandbox_url"),
        ("E2B_DOMAIN", "domain"),
    ]:
        val = os.environ.get(env_key)
        if val:
            kwargs[kwarg_key] = val
    return kwargs


@pytest.fixture
def sandbox_factory(sandbox_create_kwargs):
    created = []
    def _create(**extra):
        kwargs = dict(sandbox_create_kwargs)
        kwargs.update(extra)
        sbx = Sandbox.create(**kwargs)
        patch_sandbox_if_needed(sbx)
        created.append(sbx)
        return sbx
    yield _create
    for sbx in created:
        safe_kill_sandbox(sbx)


@pytest.fixture
def sandbox(sandbox_factory):
    return sandbox_factory()


def pytest_addoption(parser):
    parser.addoption(
        "--html-report",
        action="store",
        default="reports/e2b_compatibility_report.html",
    )


def pytest_configure(config):
    report_dir = PROJECT_ROOT / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)


def pytest_sessionfinish(session, exitstatus):
    report_path = session.config.getoption("--html-report", None)
    if report_path is None:
        report_path = "reports/e2b_compatibility_report.html"
    if not os.path.isabs(report_path):
        report_path = str(PROJECT_ROOT / report_path)
    _report_collector.generate(report_path)
    print(f"\nHTML Report: {report_path}\n")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when != "call" and not (report.when == "setup" and report.skipped):
        return

    test_name = item.name
    module = ""
    api = ""
    description = ""

    func = getattr(item, 'obj', None)
    if func and func.__doc__:
        lines = func.__doc__.strip().split("\n")
        if lines:
            description = lines[0].strip()

    for marker in item.iter_markers():
        if marker.name in ("lifecycle", "commands", "filesystem", "pty",
                           "code_interpreter", "git", "network", "snapshot",
                           "volume", "error_handling"):
            module = marker.name
            break

    if not module:
        fname = str(getattr(item, 'fspath', ''))
        module = fname.split("/")[-1].replace("test_", "").replace(".py", "")

    if func and hasattr(func, '_api'):
        api = func._api

    if report.when == "setup" and report.skipped:
        skip_reason = str(report.longrepr[2]) if report.longrepr else ""
        _report_collector.add_result(
            test_name=test_name, module=module, api=api,
            description=description, success=False, duration=0,
            skipped=True, skip_reason=skip_reason,
        )
    elif report.when == "call":
        error = ""
        details = ""
        skipped = False
        skip_reason = ""
        
        if report.skipped:
            skipped = True
            if report.longrepr:
                skip_reason = str(report.longrepr[2]) if hasattr(report.longrepr, '__getitem__') else str(report.longrepr)
        else:
            if report.failed:
                error = str(report.longrepr) if report.longrepr else ""
            if hasattr(report, 'sections'):
                for section_name, section_content in report.sections:
                    if 'stdout' in section_name:
                        details += section_content

        _report_collector.add_result(
            test_name=test_name, module=module, api=api,
            description=description, success=report.passed,
            duration=report.duration,
            details=details[:2000] if details else "",
            error=error[:2000] if error else "",
            skipped=skipped, skip_reason=skip_reason,
        )
