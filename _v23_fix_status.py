"""V23 fix: 7 个新函数缺 status:ok 字段，批量加"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

funcs = [
    'get_agents_usage',
    'get_skills_popular',
    'get_analytics_overview',
    'get_analytics_tasks',
    'get_monitoring_services',
    'get_crm_funnel',
    'get_workflows_templates',
]

count = 0
for fn in funcs:
    needle = f'def {fn}():\n    return {{\n        "data":'
    repl   = f'def {fn}():\n    return {{\n        "status": "ok",\n        "data":'
    if needle in content:
        content = content.replace(needle, repl, 1)
        count += 1
        print(f'  ✅ {fn}')

path.write_text(content, encoding='utf-8')
print(f'\n🎯 {count} 个函数补 status:ok')