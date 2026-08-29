#!/usr/bin/env python3
"""Test E2B API connection"""

import os
import sys
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# 从环境变量读取配置（不硬编码敏感信息）
E2B_API_KEY = os.environ.get("E2B_API_KEY")
E2B_API_URL = os.environ.get("E2B_API_URL")
E2B_SANDBOX_URL = os.environ.get("E2B_SANDBOX_URL")
TEMPLATE = os.environ.get("CUBE_TEMPLATE_ID")

if not E2B_API_KEY:
    print("Error: E2B_API_KEY 环境变量未设置", file=sys.stderr)
    sys.exit(1)

from e2b_code_interpreter import Sandbox

print("=" * 60)
print("E2B Connection Test")
print("=" * 60)
print(f"API Key: {E2B_API_KEY[:8]}...{E2B_API_KEY[-4:]}")
print(f"API URL: {E2B_API_URL}")
print(f"Sandbox URL: {E2B_SANDBOX_URL}")
print(f"Template: {TEMPLATE}")
print("=" * 60)

try:
    print("\nCreating sandbox...")
    sbx = Sandbox.create(
        template=TEMPLATE,
        api_key=E2B_API_KEY,
        api_url=E2B_API_URL,
        sandbox_url=E2B_SANDBOX_URL,
        timeout=120
    )
    print(f"Sandbox created: {sbx.sandbox_id}")
    
    print("\nRunning command: echo hello")
    result = sbx.commands.run("echo hello")
    print(f"Result: {result.stdout}")
    
    print("\nKilling sandbox...")
    sbx.kill()
    print("Sandbox killed successfully")
    
except Exception as e:
    import traceback
    print(f"\nError: {str(e)}")
    traceback.print_exc()