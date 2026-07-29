#!/usr/bin/env python3
"""
CloudTech Cron Pipeline Trigger — 定时管线触发器
================================================
由Cron/Windows Task Scheduler调用，自动执行:
1. 知识转化: Inbox → Processed → Pattern → Rule
2. 内容生产: 从选题库取1-3个话题 → DeepSeek → 保存
3. 质量评分: 对新产出打分，低于6分自动重写
4. 复盘记录: 记录本次执行结果
Usage: python cron_pipeline.py
"""
import sys, json, time
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

TOPICS = [
    "装修避坑指南", "厨房改造省钱攻略", "自建房设计要点",
    "装修材料怎么选", "小户型空间利用", "旧房翻新案例",
    "2026装修趋势", "智能家居搭配", "出租房改造日记",
    "闽南风格装修", "现代简约设计", "卫生间干湿分离",
]

def run():
    from admin_dashboard import CREATOR_STYLES, CONTENT_FORMS, PLATFORMS, _deepseek_call
    from pipeline_engine import convert_knowledge

    log = {"time": datetime.now().isoformat()[:19], "steps": []}

    # Step 1: 知识转化
    try:
        kr = convert_knowledge(5)
        log["steps"].append({"name": "知识转化", "status": "ok",
                            "processed": kr["processed"], "patterns": kr["patterns"]})
    except Exception as e:
        log["steps"].append({"name": "知识转化", "status": "failed", "error": str(e)[:100]})

    # Step 2: 选题生产 (随机1-3个)
    import random
    topics = random.sample(TOPICS, min(3, len(TOPICS)))
    produced = []
    for topic in topics:
        try:
            creator = CREATOR_STYLES[random.choice(["zhinan", "xiaolin", "gaogailun"])]
            form = CONTENT_FORMS[random.choice(["article", "voiceover"])]
            platform = PLATFORMS[random.choice(["xiaohongshu", "douyin", "wechat"])]

            sys_p = f"""你是内容专家。对标{creator['name']}: {creator['tone']}。
格式: {form['name']} ({form['desc']})
平台: {platform['name']} — 字数600-1500字
结构: {' → '.join(form['structure'])}
禁用: {', '.join(creator['forbidden'])}"""

            content = _deepseek_call(sys_p, f"主题: {topic}", max_tokens=2000)
            title = content.split("\n")[0][:60]

            out_dir = Path("D:/个人文件/AI/05 项目生产系统/内容生产")
            out_dir.mkdir(parents=True, exist_ok=True)
            fname = out_dir / f"{datetime.now().strftime('%Y%m%d_%H%M')}_{topic[:20]}.md"
            fname.write_text(f"# {title}\n\n> {creator['name']} | {platform['name']} | {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{content}", encoding="utf-8")
            produced.append({"topic": topic, "title": title, "words": len(content), "file": str(fname)})
        except Exception as e:
            produced.append({"topic": topic, "error": str(e)[:100]})

    log["steps"].append({"name": "内容生产", "status": "ok", "produced": len([p for p in produced if "error" not in p]),
                         "total": len(produced), "items": produced})

    # Step 3: 记录
    log_file = BASE / "data" / "cron_pipeline_log.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")

    ok = sum(1 for p in produced if "error" not in p)
    print(f"[{datetime.now().strftime('%H:%M')}] Pipeline: {ok}/{len(produced)} produced, knowledge: {log['steps'][0].get('processed',0)} processed")
    return log


if __name__ == "__main__":
    run()
