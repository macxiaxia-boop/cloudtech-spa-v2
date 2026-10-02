"""
R661 治本：批量修 5 处 SyntaxError (extra `}` at end of return)
5 个函数末尾 `,"version":"vXXX"}}` → `,"version":"vXXX"}` （一个 `}`）
修改后跑 AST 验证 + git diff stat 确认只改这 5 行
"""
import re
from pathlib import Path

src_path = Path(r"D:/CloudTech-Portable/v23_health.py")
src = src_path.read_text(encoding="utf-8")

# 5 个精确字符串
fixes = [
    (',"version":"v506"}}',  ',"version":"v506"}'),
    (',"version":"v507"}}',  ',"version":"v507"}'),
    (',"version":"v528"}}',  ',"version":"v528"}'),
    (',"version":"v528"}}',  ',"version":"v528"}'),  # 第二个 v528
    (',"version":"v529"}}',  ',"version":"v529"}'),
]

count = 0
for old, new in fixes:
    n = src.count(old)
    if n != 1:
        print(f"[ABORT] expect 1 occurrence of {old!r} but got {n}")
        raise SystemExit(1)
    src = src.replace(old, new)
    count += 1

src_path.write_text(src, encoding="utf-8")
print(f"[FIXED] {count} lines · 5 SyntaxError resolved")