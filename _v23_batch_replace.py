"""V23 批量替换 vite-spa pages 的硬编码 var()  → 标准 token (红线 #76 + #60)
SSOT: D:\\CloudTech-Portable\\web\\vite-spa\\src\\pages\\
"""
from pathlib import Path
import re

PAGES_DIR = Path(r'D:\CloudTech-Portable\web\vite-spa\src\pages')

PATTERNS = [
    ('bg-[var(--surface-base)]',     'bg-card'),
    ('bg-[var(--surface-subtle)]',    'bg-muted'),
    ('bg-[var(--surface-muted)]',     'bg-muted'),
    ('bg-[var(--surface-emphasis)]',  'bg-card'),
    ('border-[var(--border-default)]', 'border-border'),
    ('border-[var(--border-subtle)]',  'border-border'),
    ('text-[var(--text-primary)]',    'text-foreground'),
    ('text-[var(--text-secondary)]',  'text-muted-foreground'),
    ('text-[var(--text-tertiary)]',   'text-muted-foreground'),
    ('hover:bg-[var(--surface-muted)]',  'hover:bg-muted'),
    ('hover:bg-[var(--surface-subtle)]', 'hover:bg-muted'),
    ('hover:text-[var(--text-primary)]',  'hover:text-foreground'),
]

# 同时替换 components/
COMP_DIR = Path(r'D:\CloudTech-Portable\web\vite-spa\src\components')

files = list(PAGES_DIR.glob('*.tsx')) + list(COMP_DIR.glob('**/*.tsx'))

grand_total = 0
for path in files:
    try:
        content = path.read_text(encoding='utf-8')
    except Exception as e:
        print(f'  ❌ {path.name}: {e}')
        continue
    file_total = 0
    for old, new in PATTERNS:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            file_total += count
    if file_total > 0:
        path.write_text(content, encoding='utf-8')
        grand_total += file_total
        print(f'  ✅ {path.relative_to(path.parents[3])}: {file_total} 处')

print(f'\n🎯 总计替换 {grand_total} 处')