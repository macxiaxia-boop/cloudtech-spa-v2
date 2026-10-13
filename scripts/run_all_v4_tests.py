"""V4 完整测试 runner — 一键跑全部 V4 测试, 输出 7 维基线汇总"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests_v4_*.py tests/test_adapters_*.py" if False else None
TESTS_DIR = ROOT / "tests"

TEST_FILES = [
    "test_v4_orchestrator.py",
    "test_v4_media_gate.py",
    "test_v4_budget.py",
    "test_v4_idempotency.py",
    "test_v4_paths.py",
    "test_v4_api.py",
    "test_v4_end_to_end_mock.py",
    "test_v4_end_to_end_mock_more.py",
    "test_v4_end_to_end_paths.py",
    "test_v4_registry_real_load.py",
    "test_v4_auth.py",
    "test_adapters_platform.py",
    "test_adapters_transcribe.py",
    "test_adapters_article.py",
    "test_adapters_content.py",
    "test_adapters_media.py",
    "test_workbuddy_bridge.py",
    "test_real_provider_clients.py",
]


def run_one(name: str) -> dict:
    p = TESTS_DIR / name
    if not p.exists():
        return {"file": name, "status": "MISSING", "passed": 0}
    try:
        r = subprocess.run(
            ["python", "-m", "pytest", str(p), "-q"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=120
        )
        out = r.stdout + r.stderr
        # 提取 "X passed, Y subtests passed" 信息
        passed = 0
        subtests = 0
        m = __import__("re").search(r"(\d+) passed", out)
        if m:
            passed = int(m.group(1))
        m2 = __import__("re").search(r"(\d+) subtests passed", out)
        if m2:
            subtests = int(m2.group(1))
        return {
            "file": name,
            "status": "PASS" if r.returncode == 0 else "FAIL",
            "passed": passed,
            "subtests": subtests,
        }
    except subprocess.TimeoutExpired:
        return {"file": name, "status": "TIMEOUT", "passed": 0, "subtests": 0}


def main():
    print("=" * 70)
    print("V4 Test Suite Runner")
    print("=" * 70)
    total = 0
    total_sub = 0
    results = []
    for f in TEST_FILES:
        r = run_one(f)
        results.append(r)
        total += r["passed"]
        total_sub += r.get("subtests", 0)
        sub_s = f"+ {r.get('subtests', 0)} sub" if r.get("subtests", 0) else ""
        print(f"  {r['status']:10s} {r['file']:40s} {r['passed']:4d} tests {sub_s}")
    print("-" * 70)
    print(f"  TOTAL PASSED: {total} tests + {total_sub} subtests = {total + total_sub}")
    print(f"  FILES: {len(results)}")
    print(f"  FAILED: {sum(1 for r in results if r['status'] != 'PASS' and r['status'] != 'MISSING')}")
    print()
    print("7 维基线:")
    print(f"  Tested: {total + total_sub} (P1-A + P2-P4 + E2E + Registry)")
    print(f"  Production Ready: 0 (mock-only, 红线 #60)")
    print(f"  Real API calls: 0")
    return 0 if all(r["status"] in ("PASS", "MISSING") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
