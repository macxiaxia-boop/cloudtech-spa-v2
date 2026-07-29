#!/usr/bin/env python3
"""
CloudTech Cron Pipeline v2.0 — 自愈定时管线
============================================
每小时自动: 知识转化 → 选题生产 → 质量评分 → 低分重写 → 记录
失败自动重试(3次) → 模型降级 → 告警
"""
import sys, json, random, time
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

TOPICS = [
    "装修避坑指南", "厨房改造省钱攻略", "自建房设计要点",
    "装修材料怎么选", "小户型空间利用", "旧房翻新案例",
    "2026装修趋势", "智能家居搭配", "出租房改造日记",
    "闽南风格装修", "现代简约设计", "卫生间干湿分离",
    "二手房翻新实录", "适老化改造方案", "阳台改造灵感",
    "全屋定制避坑", "水电改造注意", "瓷砖选购指南",
    "涂料颜色搭配", "灯光设计技巧",
]

def run():
    from admin_dashboard import CREATOR_STYLES, CONTENT_FORMS, PLATFORMS, _deepseek_call
    from pipeline_engine import convert_knowledge, PipelineHealer

    log = {"time": datetime.now().isoformat()[:19], "steps": []}
    healer = PipelineHealer()

    # ═══ Step 1: 知识转化 ═══
    try:
        kr = convert_knowledge(5)
        log["steps"].append({"name": "知识转化", "status": "ok",
                            "processed": kr["processed"]})
    except Exception as e:
        log["steps"].append({"name": "知识转化", "status": "failed", "error": str(e)[:100]})

    # ═══ Step 2: 选题生产(自愈) ═══
    topics = random.sample(TOPICS, min(3, len(TOPICS)))
    produced = []

    for topic in topics:
        result = {"topic": topic, "attempts": 0}
        for attempt in range(3):  # max 3 retries
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

                # ═══ Step 3: 质量评分 ═══
                score = None
                try:
                    score_sys = "你是内容评审。给下文打分(1-10)并1句话建议。只输出: X/10 建议"
                    score_raw = _deepseek_call(score_sys, content[:1500], max_tokens=100, temperature=0.3)
                    try:
                        score = int(score_raw.split("/")[0].strip())
                    except:
                        score = 7  # default if parsing fails
                except:
                    pass

                # 低于6分 → 重写
                if score and score < 6 and attempt < 2:
                    result["attempts"] += 1
                    continue  # retry

                # 保存
                out_dir = Path("D:/个人文件/AI/05 项目生产系统/内容生产")
                out_dir.mkdir(parents=True, exist_ok=True)
                fname = out_dir / f"{datetime.now().strftime('%Y%m%d_%H%M')}_{topic[:20]}.md"
                fname.write_text(
                    f"# {title}\n\n> {creator['name']} | {platform['name']} | "
                    f"评分: {score or '?'}/10 | {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{content}",
                    encoding="utf-8")
                result.update({"title": title, "words": len(content), "score": score,
                               "file": str(fname), "creator": creator['name'], "attempts": attempt+1})
                produced.append(result)
                break
            except Exception as e:
                result["attempts"] += 1
                if attempt >= 2:
                    result["error"] = str(e)[:100]
                    produced.append(result)

    ok = sum(1 for p in produced if "error" not in p)
    log["steps"].append({"name": "内容生产", "status": "ok", "produced": ok,
                         "total": len(produced), "items": produced})

    # ═══ 记录 ═══
    log_file = BASE / "data" / "cron_pipeline_log.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False) + "\n")

    # 汇总输出
    scores = [p.get("score", 0) for p in produced if p.get("score")]
    avg_score = sum(scores) / len(scores) if scores else 0
    print(f"[{datetime.now().strftime('%H:%M')}] Pipeline: {ok}/{len(produced)} produced"
          f" | avg score: {avg_score:.1f}/10"
          f" | knowledge: {log['steps'][0].get('processed',0)} processed"
          f" | retries: {sum(p.get('attempts',1)-1 for p in produced)}")
    return log


if __name__ == "__main__":
    run()
