"""
R661 治本 V2：按行号修 5 处 SyntaxError
line 29815/29819/29828/29840/29849 末尾的 `}}` → `}`
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
lines = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

# 5 个目标行号（1-indexed）
target_lines = [29815, 29819, 29828, 29840, 29849]
expected_endings = [
    ',"version":"v506"}}',
    ',"version":"v507"}}',
    ',"version":"v528"}}',   # line 29828 campaign
    ',"version":"v528"}}',   # line 29840 file
    ',"version":"v529"}}',
]

count = 0
for ln_no, expected in zip(target_lines, expected_endings):
    idx = ln_no - 1
    if idx >= len(lines):
        print(f"[ABORT] line {ln_no} out of range (file has {len(lines)} lines)")
        raise SystemExit(1)
    actual = lines[idx].rstrip("\n")
    if expected not in actual:
        print(f"[ABORT] line {ln_no}: expected contains {expected!r}, got {actual[:120]!r}")
        raise SystemExit(1)
    # Replace trailing }} with } (only the very end)
    new_line = actual[:-1] + "}\n"   # 砍掉末尾多余的 }
    lines[idx] = new_line
    count += 1

src_path.write_text("".join(lines), encoding="utf-8")
print(f"[FIXED] {count} lines · 5 SyntaxError resolved")