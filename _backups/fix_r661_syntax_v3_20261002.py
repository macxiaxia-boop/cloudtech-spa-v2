"""
R661 治本 V3：line 29815/29819/29828/29840/29849 末尾 `}}` → `}`
（5 个 return 行末尾多余一个 `}`）
"""
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
lines = src_path.read_text(encoding="utf-8").splitlines(keepends=True)

# 5 个目标行号（1-indexed）—— 仅这 5 行需要修
target = [29815, 29819, 29828, 29840, 29849]
count = 0
for ln_no in target:
    idx = ln_no - 1
    line = lines[idx]
    stripped = line.rstrip("\n")
    # 检查末尾确实是 }} 且前面不是 }
    if not stripped.endswith("}}"):
        print(f"[ABORT] line {ln_no} does not end with }}: {stripped[-50:]!r}")
        raise SystemExit(1)
    # 倒数第二个字符必然是 " → 砍掉最后一个 }
    # 但要确认前面一个不是已经匹配的 }。简单做法：stripped[-2:] == "}}" 时砍掉最后一个 }
    new_stripped = stripped[:-1]  # 砍掉最后 1 个 }
    # 但还要去掉已经去掉的那个 } —— 直接 rstrip 一个 }
    lines[idx] = new_stripped + "\n"
    count += 1

src_path.write_text("".join(lines), encoding="utf-8")
print(f"[FIXED] {count} lines")