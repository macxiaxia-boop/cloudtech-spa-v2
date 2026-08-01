"""
超级混剪引擎 — Super Hybrid Editing Engine
对标筷子: 批量素材导入·智能拆分镜头·随机组合·自动成片
"""
import json, secrets, random
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
EDIT_DIR = Path("D:/个人文件/AI/云数科技/edits")
EDIT_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════
# 素材库管理
# ═══════════════════════════════════
MATERIAL_TYPES = {
    "video_clip": "视频片段", "image": "图片素材", "audio": "音频/BGM",
    "text_overlay": "文字叠加", "transition": "转场特效", "filter": "滤镜",
}

def import_material(tid: str, name: str, mtype: str, uri: str, tags: list = None, duration: float = 0) -> dict:
    """导入素材"""
    if mtype not in MATERIAL_TYPES: return {"ok": False, "error": f"未知类型: {mtype}"}
    mid = f"mat-{secrets.token_hex(4)}"
    material = {
        "id": mid, "tenant_id": tid, "name": name, "type": mtype,
        "type_name": MATERIAL_TYPES[mtype], "uri": uri,
        "tags": tags or [], "duration": duration, "usage_count": 0,
        "imported_at": datetime.now().isoformat()[:19],
    }
    mf = EDIT_DIR / f"material_{mid}.json"
    mf.write_text(json.dumps(material, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "material": material}


def list_materials(tid: str, mtype: str = "", tags: list = None) -> list:
    """列出素材"""
    materials = []
    for f in EDIT_DIR.glob("material_*.json"):
        try:
            m = json.loads(f.read_text(encoding="utf-8"))
            if m.get("tenant_id") != tid: continue
            if mtype and m.get("type") != mtype: continue
            if tags and not any(t in m.get("tags", []) for t in tags): continue
            materials.append(m)
        except Exception: pass
    return materials


# ═══════════════════════════════════
# 智能镜头拆分
# ═══════════════════════════════════
def split_clips(tid: str, scene_count: int = 5, duration_range: tuple = (3, 15)) -> list:
    """智能拆分镜头: 从素材库随机组合生成分镜"""
    clips = list_materials(tid, "video_clip") or list_materials(tid, "image")
    if not clips:
        # 无素材时生成模拟分镜
        return _generate_mock_clips(tid, scene_count, duration_range)

    scenes = []
    for i in range(min(scene_count, len(clips) * 3)):
        clip = random.choice(clips)
        duration = random.randint(*duration_range)
        scenes.append({
            "index": i + 1, "material_id": clip["id"],
            "material_name": clip["name"], "duration": duration,
            "transition": random.choice(["cut", "fade", "slide", "zoom"]),
            "effect": random.choice(["none", "blur_in", "scale_up", "light_leak"]),
        })
    return scenes[:scene_count]


def _generate_mock_clips(tid: str, count: int, dr: tuple) -> list:
    scenes = []
    scene_types = ["远景建立", "中景展示", "特写细节", "人物出镜", "空间漫游", "材质纹理", "光影氛围", "功能演示"]
    for i in range(count):
        scenes.append({
            "index": i + 1, "material_id": f"mock-{i+1}",
            "material_name": scene_types[i % len(scene_types)],
            "duration": random.randint(*dr),
            "transition": random.choice(["cut", "fade"]),
            "effect": "none",
        })
    return scenes


# ═══════════════════════════════════
# 随机组合引擎
# ═══════════════════════════════════
def generate_mashup(tid: str, topic: str, variant_count: int = 3, scene_count: int = 6) -> dict:
    """随机组合生成混剪方案: 同主题N个变体"""
    variants = []
    for v in range(variant_count):
        scenes = split_clips(tid, scene_count)
        total_duration = sum(s["duration"] for s in scenes)
        variant = {
            "id": f"var-{secrets.token_hex(3)}", "topic": topic,
            "variant_index": v + 1, "scenes": scenes,
            "total_duration": total_duration,
            "bgm": random.choice(["轻快温馨", "激昂节奏", "舒缓沉浸", "科技现代"]),
            "style": random.choice(["cinematic", "vlog", "commercial", "documentary"]),
        }
        variants.append(variant)

    # 保存混剪方案
    edit_id = f"edit-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3)}"
    edit = {
        "id": edit_id, "tenant_id": tid, "topic": topic,
        "variants": variants, "total_variants": variant_count,
        "total_duration": sum(v["total_duration"] for v in variants),
        "created_at": datetime.now().isoformat()[:19],
    }
    ef = EDIT_DIR / f"{edit_id}.json"
    ef.write_text(json.dumps(edit, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"ok": True, "edit": edit}


# ═══════════════════════════════════
# 自动成片
# ═══════════════════════════════════
def auto_compose(tid: str, edit_id: str, output_format: str = "9:16") -> dict:
    """自动成片: 将混剪方案渲染为完整视频方案"""
    ef = EDIT_DIR / f"{edit_id}.json"
    if not ef.exists(): return {"ok": False, "error": "混剪方案不存在"}
    edit = json.loads(ef.read_text(encoding="utf-8"))

    # 为每个变体生成完整脚本
    for variant in edit["variants"]:
        script_lines = [f"# {variant['topic']} - 变体{variant['variant_index']}"]
        script_lines.append(f"## 风格: {variant['style']} | BGM: {variant['bgm']} | 时长: {variant['total_duration']}s")
        script_lines.append(f"## 格式: {output_format}")
        script_lines.append("")
        for s in variant["scenes"]:
            script_lines.append(f"[Scene {s['index']}·{s['duration']}s] {s['material_name']}")
            script_lines.append(f"  转场: {s['transition']} | 特效: {s['effect']}")
        script_lines.append("")
        script_lines.append("## 输出: 即梦/剪映/Seedance API调用")
        variant["script"] = "\n".join(script_lines)

    # 保存完整方案
    script_file = EDIT_DIR / f"script_{edit_id}.md"
    full_script = "\n\n".join(v["script"] for v in edit["variants"])
    script_file.write_text(full_script, encoding="utf-8")

    edit["rendered"] = True
    edit["script_file"] = str(script_file)
    edit["output_format"] = output_format
    ef.write_text(json.dumps(edit, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"ok": True, "edit": edit, "script": str(script_file)}
