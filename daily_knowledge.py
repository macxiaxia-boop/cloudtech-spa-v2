#!/usr/bin/env python3
"""
每日知识转化 — Daily Knowledge Pipeline
=========================================
STEP 1: 扫描 business_state.json → 今日完成且有产出物的任务
STEP 2: 读取产出物 → 判断是否有可复用模式
STEP 3: 提取模式 → 写入 Obsidian Patterns
STEP 4: 周日合并 ≥2相似模式 → 升级为规则 → 写入 RULES.md
STEP 5: 推送摘要(≤200字)
"""
import json, re, sys
from pathlib import Path
from datetime import datetime, timedelta

STATE_FILE = Path("C:/Users/xinzh/.openclaw/workspace/state/business_state.json")
PATTERNS_DIR = Path("D:/个人文件/AI/Patterns")
RULES_FILE = Path("D:/个人文件/AI/Knowledge/RULES.md")
TODAY = datetime.now().strftime("%Y-%m-%d")
IS_SUNDAY = datetime.now().weekday() == 6

# ═══════════════════════════════════
# STEP 1: 扫描今日已完成任务
# ═══════════════════════════════════
def scan_today():
    if not STATE_FILE.exists():
        print("⚠️ business_state.json 不存在")
        return []

    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    tasks = data.get("workQueue", [])

    today_tasks = []
    for t in tasks:
        if t.get("status") != "completed":
            continue
        if not t.get("outputPath"):
            continue
        completed_at = str(t.get("completedAt", ""))
        # 检查是否是今天完成的（含跨天模糊匹配）
        if TODAY in completed_at or (
            datetime.now() - _parse_time(completed_at) < timedelta(hours=36)
            and datetime.now().strftime("%d") == _parse_time(completed_at).strftime("%d")
        ):
            today_tasks.append(t)
        # 也匹配最近24h内的
        elif _parse_time(completed_at) and (
            datetime.now() - _parse_time(completed_at) < timedelta(hours=24)
        ):
            today_tasks.append(t)

    return today_tasks


def _parse_time(ts_str):
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
        try:
            ts = ts_str.replace("+08:00", "").replace("Z", "")
            return datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            pass
    return None


# ═══════════════════════════════════
# STEP 2: 读取产出物 + 判断可复用模式
# ═══════════════════════════════════
def analyze_task(task):
    path = Path(task["outputPath"])
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")[:3000]
    except Exception:
        return None

    # 判断标准: 同样的方法可以用在≥2个不同场景？
    patterns_found = []

    # 检测1: "对比/排名/检测" 方法 → geo_research 模式
    if task.get("type") == "geo_research" or any(
        kw in (task.get("topic", "") + content[:500])
        for kw in ["排名", "检测", "对比", "搜索可见度"]
    ):
        patterns_found.append({
            "scene": "GEO关键词排名检测",
            "method": "用DeepSeek/豆包/Kimi模拟搜索 + 逐条记录排名 + 对比竞品可见度",
            "boundary": "仅适用于有明确搜索场景的关键词，品牌词/泛词检测价值低",
        })

    # 检测2: "小红书版/适配" 方法 → content_adaptation 模式
    if "小红书" in task.get("topic", "") or "小红书" in task.get("format", ""):
        patterns_found.append({
            "scene": "多平台内容适配",
            "method": "长文→小红书版：压缩到600-800字 + emoji密度提高 + 话题标签 + 第一人称视角",
            "boundary": "技术/学术内容不适用，需要专业受众的内容不宜过度简化",
        })

    # 检测3: "检查/扫描/填充" 方法 → batch_audit 模式
    if task.get("type") in ("system_maintenance",) or any(
        kw in (task.get("topic", "")) for kw in ["检查", "扫描", "填充", "催办"]
    ):
        patterns_found.append({
            "scene": "素材库/系统批量审计",
            "method": "遍历目标目录→统计覆盖率→生成缺口报告→自动填充脚本",
            "boundary": "适用于结构化素材库，非结构化/创意型素材不适配",
        })

    # 检测4: 通用：产出物包含"步骤/流程/清单"
    if re.search(r'(步骤[1一]|流程|清单|SOP|checklist)', content[:1000], re.IGNORECASE):
        patterns_found.append({
            "scene": "SOP流程化",
            "method": "将重复性任务拆解为步骤清单 → 每步有验收标准 → 可委派给Agent执行",
            "boundary": "创造性工作不适合过度流程化，保留人工判断节点",
        })

    return patterns_found if patterns_found else None


# ═══════════════════════════════════
# STEP 3: 写入 Obsidian Pattern
# ═══════════════════════════════════
def write_pattern(task, pattern):
    PATTERNS_DIR.mkdir(parents=True, exist_ok=True)

    safe_desc = re.sub(r'[\\/:*?"<>|]', '_', pattern["scene"])[:20]
    filename = f"pattern-{TODAY}-{safe_desc}.md"
    filepath = PATTERNS_DIR / filename

    if filepath.exists():
        return None  # 不重复写入

    content = f"""#pattern

场景: {pattern['scene']}
方法: {pattern['method']}
边界: {pattern['boundary']}
来源: {task['id']} - {TODAY}
"""
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


# ═══════════════════════════════════
# STEP 4: 周日合并 → 规则
# ═══════════════════════════════════
def merge_to_rules():
    if not IS_SUNDAY:
        return None

    this_week = []
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    for f in sorted(PATTERNS_DIR.glob("pattern-*.md")):
        if f.stat().st_mtime > datetime.strptime(cutoff, "%Y-%m-%d").timestamp():
            this_week.append(f)

    if len(this_week) < 2:
        return None

    # 读取所有本周pattern
    all_patterns = []
    for f in this_week:
        try:
            text = f.read_text(encoding="utf-8")
            scene = re.search(r'场景:\s*(.+)', text)
            method = re.search(r'方法:\s*(.+)', text)
            if scene and method:
                all_patterns.append({"scene": scene.group(1), "method": method.group(1), "file": f.name})
        except Exception:
            pass

    # 合并相似场景
    from collections import Counter
    scenes = Counter(p["scene"] for p in all_patterns)
    merged = {s: [p for p in all_patterns if p["scene"] == s] for s, c in scenes.items() if c >= 2}

    if not merged:
        return None

    # 写入规则
    RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    rules_content = f"# RULES — 自动生成 {TODAY}\n\n"
    for scene, patterns in merged.items():
        rules_content += f"## Rule: {scene}\n"
        rules_content += f"**When:** {patterns[0]['scene']}\n"
        rules_content += f"**Then:** {patterns[0]['method']}\n"
        rules_content += f"**Because:** 本周出现{len(patterns)}次 → 已验证为可复用模式\n"
        rules_content += f"**Sources:** {', '.join(p['file'] for p in patterns)}\n\n"

    if RULES_FILE.exists():
        existing = RULES_FILE.read_text(encoding="utf-8")
        # 追加而非覆盖
        RULES_FILE.write_text(existing + "\n" + rules_content, encoding="utf-8")
    else:
        RULES_FILE.write_text(rules_content, encoding="utf-8")

    return len(merged)


# ═══════════════════════════════════
# STEP 5: 推送摘要
# ═══════════════════════════════════
def push_summary(scanned, patterns_written, rules_merged):
    # 统计本周累计
    this_week_patterns = len(list(PATTERNS_DIR.glob("pattern-*.md"))) if PATTERNS_DIR.exists() else 0

    lines = ["🔔 今日知识转化"]

    if patterns_written == 0:
        lines.append("今日无新模式")
    else:
        lines.append(f"扫描{scanned}个任务 → 发现{patterns_written}个模式 → 已写入Patterns")
        # 列出模式摘要
        for pw in patterns_written[:3]:
            lines.append(f"  • {pw}")

    lines.append(f"本周累计: {this_week_patterns}个模式")

    if rules_merged:
        lines.append(f"🎯 周日合并: {rules_merged}个场景升级为规则 → RULES.md")

    summary = "\n".join(lines)
    if len(summary) > 200:
        summary = summary[:197] + "..."

    print(summary)
    return summary


# ═══════════════════════════════════
# MAIN
# ═══════════════════════════════════
def run():
    print(f"[{datetime.now().strftime('%H:%M')}] Daily Knowledge Pipeline")

    # STEP 1
    tasks = scan_today()
    if not tasks:
        print("  今日无已完成任务（有产出物）")
        push_summary(0, 0, 0)
        return {"scanned": 0, "patterns": 0, "rules": 0}

    # STEP 2-3
    patterns_written = []
    for task in tasks:
        patterns = analyze_task(task)
        if patterns:
            for p in patterns:
                path = write_pattern(task, p)
                if path:
                    patterns_written.append(p["scene"])
                    print(f"  ✅ pattern: {p['scene']}")

    # STEP 4
    rules_merged = merge_to_rules() if IS_SUNDAY else 0

    # STEP 5
    summary = push_summary(len(tasks), len(patterns_written), rules_merged)

    return {
        "scanned": len(tasks),
        "patterns": len(patterns_written),
        "rules": rules_merged or 0,
        "summary": summary,
    }


if __name__ == "__main__":
    run()
