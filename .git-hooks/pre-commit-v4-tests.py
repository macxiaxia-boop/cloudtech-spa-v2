"""V4 — Pre-commit hook: 跑全部 V4 测试, 不通过则阻止 commit
红线 #87 #1269: 强制验证跑通才能进版本
用法: ln -s ../../.git-hooks/pre-commit-v4-tests.py .git/hooks/pre-commit
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_GLOB = "tests/test_v4_*.py tests/test_adapters_*.py"


def main():
    print("[pre-commit-v4] running V4 test suite...")
    r = subprocess.run(
        ["python", "-m", "pytest", *TEST_GLOB.split(), "-q", "--tb=short"],
        cwd=str(ROOT),
    )
    if r.returncode != 0:
        print("[pre-commit-v4] ❌ tests FAILED, commit blocked")
        return 1
    print("[pre-commit-v4] ✅ tests PASSED, commit allowed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
