"""V23 fix v2: 更宽的匹配 — 在 7 个特定函数的 return { 后插入 status:ok"""
from pathlib import Path

path = Path(r'D:\CloudTech-Portable\v23_health.py')
content = path.read_text(encoding='utf-8')

# 找每个函数的 return { 后面插入 status:ok
# 用 7 个函数名锚定
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
    # 匹配 def fn(): ... "data":
    needle = f'def {fn}():\n    return {{\n        "data":'
    if needle in content:
        # 检查后面是否已经有 status:"ok"
        idx = content.index(needle)
        after = content[idx+len(needle):idx+len(needle)+30]
        if '"status": "ok"' in after:
            print(f'  ⏭️ {fn} 已有 status')
            continue
        # 没有 status，加
        repl = f'def {fn}():\n    return {{\n        "status": "ok",\n        "data":'
        content = content.replace(needle, repl, 1)
        count += 1
        print(f'  ✅ {fn} 加 status:ok')
    else:
        # 备选: def fn():\n    """docstring"""\n    return {\n        "data":
        alt_needle = f'def {fn}():\n    """'
        if alt_needle in content:
            # 找 return { 后面 state ok 替换
            # 先找 function 开始
            fn_start = content.index(alt_needle)
            # 找这个 function 里第一个 return { 后第一个 "data":
            after_fn = content[fn_start:]
            # 找 "data": 位置
            data_pos = after_fn.find('"data":')
            if data_pos > 0:
                # 找 data_pos 前的 "{ \n        " 位置
                before_data = after_fn[:data_pos]
                # 在 "data": 前插入 "status": "ok",\n        "data":
                last_brace = before_data.rfind('{')
                if last_brace >= 0:
                    insert_pos = last_brace + 1
                    new_fn = (after_fn[:insert_pos] +
                              '\n        "status": "ok",' +
                              after_fn[insert_pos:])
                    content = content[:fn_start] + new_fn
                    count += 1
                    print(f'  ✅ {fn} 通过 alt 模式加 status:ok')

path.write_text(content, encoding='utf-8')
print(f'\n🎯 {count} 个函数补 status:ok')