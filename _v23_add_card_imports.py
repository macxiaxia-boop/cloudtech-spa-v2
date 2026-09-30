"""V23 批量加 Card/Badge imports 到 4 page (SettingsTeam/Analytics/Monitoring/Tasks)"""
from pathlib import Path

PAGES = Path(r'D:\CloudTech-Portable\web\vite-spa\src\pages')
files = ['SettingsTeam.tsx', 'Analytics.tsx', 'Monitoring.tsx', 'Tasks.tsx']

count = 0
for name in files:
    path = PAGES / name
    if not path.exists():
        print(f'  ❌ {name}: 不存在')
        continue
    content = path.read_text(encoding='utf-8')
    if 'Card,' in content or 'import { Card' in content or 'Card }' in content:
        print(f'  ⏭️ {name}: 已有 Card import')
        continue
    # 找 lucide-react import 行后插入
    lines = content.split('\n')
    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if not inserted and "from 'lucide-react';" in line:
            # 在这行后插入 Card imports
            indent = len(line) - len(line.lstrip())
            sp = ' ' * indent
            new_lines.append(f"{sp}import {{ Card, CardContent, CardHeader, CardTitle }} from '@/components/ui/card';")
            new_lines.append(f"{sp}import {{ Badge }} from '@/components/ui/badge';")
            new_lines.append(f"{sp}import {{ Input }} from '@/components/ui/input';")
            inserted = True
    if inserted:
        new_content = '\n'.join(new_lines)
        path.write_text(new_content, encoding='utf-8')
        count += 1
        print(f'  ✅ {name}: +3 imports')

print(f'\n🎯 {count}/{len(files)} 加 imports')