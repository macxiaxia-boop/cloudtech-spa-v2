"""V4 — Pre-deploy verification gate
按红线 #60 #87: 不通过则拒绝标 Production Ready
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    errors = []
    warnings = []

    # 1. 跑所有测试 (用 pathlib 显式列举, 避免 shell glob 跨进程问题)
    print("[V4-VERIFY] running full test suite...")
    test_files = sorted(
        list((ROOT / "tests").glob("test_v4_*.py")) +
        list((ROOT / "tests").glob("test_adapters_*.py")) +
        list((ROOT / "tests").glob("test_workbuddy_*.py"))
    )
    test_paths = [str(p.relative_to(ROOT)) for p in test_files]
    r = subprocess.run(
        ["python", "-m", "pytest", *test_paths, "-q", "--tb=short"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    if r.returncode != 0:
        errors.append(f"tests FAILED: returncode={r.returncode}\n{r.stdout[-500:]}")
    else:
        print(f"[V4-VERIFY] ✅ tests pass ({len(test_paths)} files)")

    # 2. 跑 migration dry-run audit
    print("[V4-VERIFY] running migration audit...")
    r2 = subprocess.run(
        ["python", "scripts/run_v4_migration.py"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    if r2.returncode != 0 or "DRY-RUN" not in r2.stdout:
        errors.append("migration audit failed")
    else:
        print(f"[V4-VERIFY] ✅ migration dry-run OK")

    # 3. 检查 .env 未触碰 (ATLASCLOUD_API_KEY 仍在, 不被脚本删)
    claude_json = Path("C:/Users/xinzh/.claude.json")
    if claude_json.exists():
        txt = claude_json.read_text(encoding="utf-8", errors="ignore")
        if "ATLASCLOUD_API_KEY" in txt:
            print(f"[V4-VERIFY] ⚠️ ATLASCLOUD_API_KEY 字段仍存在 (L4 待拍处置)")

    # 4. 检查 git 工作区未 commit
    r3 = subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT), capture_output=True, text=True)
    if r3.stdout.strip():
        print(f"[V4-VERIFY] ⚠️ git 工作区有 {len(r3.stdout.strip().split(chr(10)))} 个未 commit 改动 (按 CLAUDE.md 等 user 拍 commit)")

    # 5. 检查 production ready 标记
    for f in [
        ROOT / "workflows/v4/P1A_EVIDENCE.md",
        ROOT / "adapters" / "platform" / "EVIDENCE.md",
        ROOT / "adapters" / "media" / "EVIDENCE.md",
    ]:
        if f.exists():
            txt = f.read_text(encoding="utf-8", errors="ignore")
            if "Production Ready: YES" in txt or "PRODUCTION READY" in txt:
                errors.append(f"{f.name} 标 Production Ready 但 mock-only, 红线 #60 禁止")

    print()
    print("=" * 70)
    if errors:
        print("[V4-VERIFY] ❌ FAILED")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print("[V4-VERIFY] ✅ PASSED (mock-only baseline)")
        print(f"  Warnings: {len(warnings)}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
