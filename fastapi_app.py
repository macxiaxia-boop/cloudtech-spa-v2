"""
CloudTech v2.1 — FastAPI 子应用 (与Flask并行运行)
==================================================
提供: 异步API端点 + 自动OpenAPI文档 + Prometheus指标 + 类型安全
运行: uvicorn fastapi_app:app --port 5100
"""
import os, json, time, hashlib, secrets
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BASE = Path(__file__).parent

app = FastAPI(
    title="CloudTech API v2",
    version="2.1.0",
    description="云数科技 AI数字营销中台 — 异步API + 自动文档",
    docs_url="/api/v2/docs",
    openapi_url="/api/v2/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5099", "http://127.0.0.1:5099", "http://localhost:8501"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════
# Models
# ═══════════════════════════════════

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)

class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    content_form: str = Field(default="voiceover", pattern="^(voiceover|persona|storytelling|mashup|article|short_video|renovation_showcase)$")
    creator: str = Field(default="zhinan", pattern="^(zhinan|xiaolin|gaogailun|xiaoa|family)$")
    platform: str = Field(default="douyin", pattern="^(douyin|xiaohongshu|wechat|zhihu|bilibili|pengyouquan)$")
    word_count: int = Field(default=1500, ge=50, le=10000)
    hook_type: Optional[str] = None
    story_formula: Optional[str] = None
    expression: Optional[str] = None
    extra: str = ""

class TopicDiscoveryRequest(BaseModel):
    domain: str = Field(..., min_length=1, max_length=200)
    creators: list[str] = Field(default=["zhinan", "xiaolin"], min_length=1)
    count: int = Field(default=5, ge=1, le=10)

class RepurposeExtractRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000, pattern="^https?://")

class RepurposeRewriteRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=50000)
    style: str = "去AI腔"
    custom_prompt: str = ""
    folder: str = ""

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float

# ═══════════════════════════════════
# Helpers
# ═══════════════════════════════════

START_TIME = time.time()

async def deepseek_call(system_prompt: str, user_prompt: str, max_tokens=2000, temperature=0.7) -> str:
    import urllib.request as ur
    data = json.dumps({
        "model": "deepseek-v4-pro", "max_tokens": max_tokens, "temperature": temperature,
        "messages": [{"role": "system", "content": system_prompt},
                     {"role": "user", "content": user_prompt}]
    }).encode("utf-8")
    req = ur.Request("https://api.deepseek.com/anthropic/v1/messages", data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "anthropic-version": "2023-06-01"
    })
    with ur.urlopen(req, timeout=180) as r:
        result = json.loads(r.read().decode())
        text = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        return text


async def verify_admin(x_admin_token: str = Header(None)):
    if not x_admin_token:
        raise HTTPException(401, "X-Admin-Token required")
    try:
        from auth import AuthManager
        auth = AuthManager()
        payload = auth.verify_jwt(x_admin_token)
        if not payload:
            raise HTTPException(401, "Invalid token")
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Auth error")


# ═══════════════════════════════════
# Routes — System
# ═══════════════════════════════════

@app.get("/api/v2/health", response_model=HealthResponse, tags=["System"])
async def health():
    return {"status": "ok", "version": "2.1.0", "uptime_seconds": time.time() - START_TIME}

@app.get("/api/v2/metrics", tags=["System"])
async def metrics():
    """Prometheus-compatible metrics endpoint"""
    import shutil
    lines = [
        "# HELP cloudtech_info CloudTech version info",
        'cloudtech_info{version="2.1.0"} 1',
        f"# HELP cloudtech_uptime_seconds Server uptime",
        f"cloudtech_uptime_seconds {time.time() - START_TIME:.0f}",
    ]
    try:
        usage = shutil.disk_usage("C:\\")
        lines.append("# HELP system_disk_free_bytes Disk free space on C:")
        lines.append(f"system_disk_free_bytes {usage.free}")
    except Exception:
        pass
    return PlainTextResponse("\n".join(lines) + "\n")


# ═══════════════════════════════════
# Routes — Auth
# ═══════════════════════════════════

@app.post("/api/v2/auth/login", tags=["Auth"])
async def login(req: LoginRequest):
    from auth import AuthManager
    auth = AuthManager()
    result = auth.authenticate_user(req.email, req.password)
    if not result:
        raise HTTPException(401, "邮箱或密码错误")
    return result


# ═══════════════════════════════════
# Routes — Content Creation
# ═══════════════════════════════════

@app.get("/api/v2/create/styles", tags=["Content Creation"])
async def list_styles():
    """List 4 creator styles"""
    from admin_dashboard import CREATOR_STYLES, PLATFORMS
    styles = [{"id": v["id"], "name": v["name"], "icon": v["icon"],
               "tagline": v["tagline"], "best_platforms": v["best_platforms"]}
              for v in CREATOR_STYLES.values()]
    return {"status": "ok", "styles": styles, "platforms": PLATFORMS}

@app.get("/api/v2/create/forms", tags=["Content Creation"])
async def list_forms():
    """List 6 content forms + hook/story/expression systems"""
    from admin_dashboard import CONTENT_FORMS, HOOK_TYPES, STORY_FORMULAS, EXPRESSION_STYLES
    return {"status": "ok", "forms": list(CONTENT_FORMS.values()),
            "hook_types": HOOK_TYPES, "story_formulas": STORY_FORMULAS,
            "expression_styles": EXPRESSION_STYLES}

@app.post("/api/v2/create/generate", tags=["Content Creation"])
async def generate_content(req: GenerateRequest):
    """Generate content with full creator style system"""
    from admin_dashboard import CONTENT_FORMS, CREATOR_STYLES, PLATFORMS, HOOK_TYPES, STORY_FORMULAS, EXPRESSION_STYLES
    form = CONTENT_FORMS.get(req.content_form, CONTENT_FORMS["voiceover"])
    creator = CREATOR_STYLES.get(req.creator, CREATOR_STYLES["zhinan"])
    platform = PLATFORMS.get(req.platform, PLATFORMS["douyin"])

    parts = [f"你是顶尖内容创作者。\n## {form['name']}: {form['desc']}\n结构: {' → '.join(form['structure'])}"]
    parts.append(f"## 对标: {creator['name']} — {creator['tone']}")
    parts.append(f"## 平台: {platform['name']} ({platform['style']}) — {req.word_count}字")

    if req.hook_type and req.hook_type in HOOK_TYPES:
        h = HOOK_TYPES[req.hook_type]; parts.append(f"## 钩子: {h['name']} — {h['formula']}")
    if req.story_formula and req.story_formula in STORY_FORMULAS:
        s = STORY_FORMULAS[req.story_formula]; parts.append(f"## 叙事: {s['name']} — {s['formula']}")
    if req.expression and req.expression in EXPRESSION_STYLES:
        e = EXPRESSION_STYLES[req.expression]; parts.append(f"## 表达: {e['name']} — {e['desc']}")

    system_prompt = "\n".join(parts)
    user_prompt = f"主题: {req.topic}\n额外: {req.extra or '无'}"
    try:
        raw = await deepseek_call(system_prompt, user_prompt, max_tokens=4000)
        title, body = raw, raw
        if "---TITLE---" in raw:
            parts_raw = raw.split("---BODY---")
            title = parts_raw[0].replace("---TITLE---", "").strip()
            body = parts_raw[1].strip() if len(parts_raw) > 1 else raw
        return {"status": "ok", "content_form": form["name"], "creator": creator["name"],
                "platform": platform["name"], "title": title, "body": body, "word_count_actual": len(body)}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/v2/create/topic-discovery", tags=["Content Creation"])
async def topic_discovery(req: TopicDiscoveryRequest):
    from admin_dashboard import CREATOR_STYLES
    cns = [CREATOR_STYLES[c]["name"] for c in req.creators if c in CREATOR_STYLES]
    system = f"发现「{req.domain}」{req.count}个选题。对标: {', '.join(cns)}。格式: 标题|创作者|平台|字数|角度|为什么|大纲"
    try:
        raw = await deepseek_call(system, f"领域: {req.domain}", max_tokens=2500, temperature=0.8)
        briefs = []
        for block in raw.split("---BRIEF---"):
            if not block.strip(): continue
            lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
            if len(lines) < 5: continue
            first = lines[0].split("|")
            briefs.append({"title": first[0].strip() if len(first)>0 else "",
                          "creator": first[1].strip() if len(first)>1 else cns[0],
                          "platform": first[2].strip() if len(first)>2 else "", "angle": first[4].strip() if len(first)>4 else ""})
        return {"status": "ok", "domain": req.domain, "briefs": briefs}
    except Exception as e:
        raise HTTPException(500, str(e))


# ═══════════════════════════════════
# Routes — Repurpose
# ═══════════════════════════════════

@app.post("/api/v2/repurpose/extract", tags=["Repurpose"])
async def repurpose_extract(req: RepurposeExtractRequest):
    from repurpose_pipeline import extract_content
    result = extract_content(req.url)
    return {"status": "ok", "data": {"platform": result["platform"], "title": result["title"],
            "author": result["author"], "text": result["text"][:8000], "text_length": len(result["text"]),
            "image_count": len(result["images"]), "downloaded_images": len(result.get("downloaded_images", [])),
            "folder": result.get("folder", "")}}

@app.post("/api/v2/repurpose/rewrite", tags=["Repurpose"])
async def repurpose_rewrite(req: RepurposeRewriteRequest):
    from repurpose_pipeline import ai_rewrite
    result = ai_rewrite(req.text, req.style, req.custom_prompt, req.folder)
    return {"status": "ok", "data": result}


# ═══════════════════════════════════
# Routes — Admin (protected)
# ═══════════════════════════════════

@app.get("/api/v2/admin/dashboard", tags=["Admin"])
async def admin_dashboard(user=Depends(verify_admin)):
    import platform as pf, socket
    from database import Database
    db = Database().connect()
    r = db.fetch_one("SELECT COUNT(*) as c FROM users")
    return {"status": "ok", "version": "2.1.0", "python": pf.python_version(),
            "hostname": socket.gethostname(), "total_users": r["c"] if r else 0}

@app.get("/api/v2/admin/users", tags=["Admin"])
async def admin_users(search: str = "", page: int = 1, limit: int = 20, user=Depends(verify_admin)):
    from database import Database
    db = Database().connect()
    if search:
        rows = db.fetch_all("SELECT id,email,name,role,created_at FROM users WHERE email LIKE ? OR name LIKE ? LIMIT ? OFFSET ?",
                           [f"%{search}%", f"%{search}%", limit, (page-1)*limit])
    else:
        rows = db.fetch_all("SELECT id,email,name,role,created_at FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
                           [limit, (page-1)*limit])
    return {"status": "ok", "users": [dict(r) for r in rows], "page": page, "limit": limit}


# ═══════════════════════════════════
# Startup
# ═══════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    print("CloudTech FastAPI v2.1 — http://localhost:5100")
    print("API Docs: http://localhost:5100/api/v2/docs")
    uvicorn.run(app, host="127.0.0.1", port=5100, log_level="info")
