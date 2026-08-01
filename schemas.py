"""
CloudTech v2.1 — Pydantic 请求/响应模型
所有API输入校验 + 类型安全 + 自动文档生成基础
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum


# ═══════════════════════════════════════
# Auth
# ═══════════════════════════════════════

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=200, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    password: str = Field(..., min_length=6, max_length=128)

class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=200)
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field(..., min_length=1, max_length=100)
    company: Optional[str] = Field(default="", max_length=200)
    plan: Optional[str] = Field(default="starter")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("邮箱格式不正确")
        return v.strip().lower()


# ═══════════════════════════════════════
# Content Creation
# ═══════════════════════════════════════

class CreatorEnum(str, Enum):
    zhinan = "zhinan"
    xiaolin = "xiaolin"
    gaogailun = "gaogailun"
    xiaoa = "xiaoa"
    family = "family"

class ContentFormEnum(str, Enum):
    voiceover = "voiceover"
    persona = "persona"
    storytelling = "storytelling"
    mashup = "mashup"
    article = "article"
    short_video = "short_video"
    renovation_showcase = "renovation_showcase"

class PlatformEnum(str, Enum):
    douyin = "douyin"
    xiaohongshu = "xiaohongshu"
    wechat = "wechat"
    zhihu = "zhihu"
    bilibili = "bilibili"
    pengyouquan = "pengyouquan"

class HookEnum(str, Enum):
    H1 = "H1"
    H2 = "H2"
    H3 = "H3"
    H4 = "H4"
    H5 = "H5"
    H6 = "H6"

class StoryFormulaEnum(str, Enum):
    wealth = "wealth"
    cognitive = "cognitive"
    curiosity = "curiosity"
    ranking = "ranking"

class ExpressionEnum(str, Enum):
    bestie = "bestie"
    scholar = "scholar"
    business = "business"


class TopicDiscoveryRequest(BaseModel):
    domain: str = Field(..., min_length=1, max_length=200)
    creators: List[CreatorEnum] = Field(default=["zhinan", "xiaolin"], min_length=1, max_length=4)
    count: int = Field(default=5, ge=1, le=10)

class GenerateV2Request(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    content_form: ContentFormEnum = Field(default=ContentFormEnum.voiceover)
    creator: CreatorEnum = Field(default=CreatorEnum.zhinan)
    platform: PlatformEnum = Field(default=PlatformEnum.douyin)
    word_count: int = Field(default=1500, ge=50, le=10000)
    hook_type: Optional[HookEnum] = None
    story_formula: Optional[StoryFormulaEnum] = None
    expression: Optional[ExpressionEnum] = None
    extra: Optional[str] = Field(default="", max_length=1000)

class MultiPlatformRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    base_content: Optional[str] = Field(default="", max_length=10000)
    creator: CreatorEnum = Field(default=CreatorEnum.zhinan)
    platforms: List[PlatformEnum] = Field(default=["xiaohongshu", "douyin", "wechat"], min_length=1, max_length=6)

class StyleCloneRequest(BaseModel):
    text: str = Field(..., min_length=100, max_length=10000)

class DeaiCheckRequest(BaseModel):
    text: str = Field(..., min_length=50, max_length=10000)


# ═══════════════════════════════════════
# Repurpose
# ═══════════════════════════════════════

class RepurposeExtractRequest(BaseModel):
    url: str = Field(..., min_length=5, max_length=2000)
    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL必须以http://或https://开头")
        return v.strip()

class RepurposeRewriteRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=50000)
    style: Optional[str] = Field(default="去AI腔", max_length=50)
    custom_prompt: Optional[str] = Field(default="", max_length=2000)
    folder: Optional[str] = Field(default="", max_length=500)


# ═══════════════════════════════════════
# Zhuangqi
# ═══════════════════════════════════════

class ZhuangqiBriefRequest(BaseModel):
    city: str = Field(default="厦门", min_length=1, max_length=50)
    content_type: str = Field(default="小红书图文", min_length=1, max_length=50)
    context: Optional[dict] = None

class ZhuangqiWeekPlanRequest(BaseModel):
    city: str = Field(default="厦门", min_length=1, max_length=50)
    accounts: Optional[List[dict]] = None


# ═══════════════════════════════════════
# GEO
# ═══════════════════════════════════════

class GeoKeywordRequest(BaseModel):
    city: str = Field(default="厦门", min_length=1, max_length=50)
    keywords: List[str] = Field(..., min_length=1, max_length=10)
    @field_validator("keywords")
    @classmethod
    def trim_keywords(cls, v):
        return [kw.strip() for kw in v if kw.strip()]

class GeoRankRequest(BaseModel):
    city: str = Field(default="厦门", min_length=1, max_length=50)
    keyword: str = Field(..., min_length=1, max_length=200)
    platforms: List[str] = Field(default=["DeepSeek", "豆包", "Kimi"])

class GeoContentRequest(BaseModel):
    city: str = Field(default="厦门", min_length=1, max_length=50)
    keyword: str = Field(..., min_length=1, max_length=200)
    platform: str = Field(default="小红书", max_length=50)
    tone: str = Field(default="实用避坑", max_length=50)


# ═══════════════════════════════════════
# Social / Trends
# ═══════════════════════════════════════

class SocialSearchRequest(BaseModel):
    city: str = Field(default="厦门", min_length=1, max_length=50)
    keyword: str = Field(..., min_length=1, max_length=200)
    count: int = Field(default=5, ge=1, le=20)

class TrendSearchRequest(BaseModel):
    query: Optional[str] = Field(default="", max_length=200)
    max_results: int = Field(default=5, ge=1, le=20)
    city: Optional[str] = Field(default="厦门", max_length=50)
    keyword: Optional[str] = Field(default="", max_length=200)


# ═══════════════════════════════════════
# Prompts
# ═══════════════════════════════════════

class PromptGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    scene: str = Field(default="content", max_length=50)
    requirements: Optional[str] = Field(default="", max_length=1000)

class PromptCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scene: str = Field(default="custom", max_length=50)
    system_prompt: str = Field(default="", max_length=10000)
    user_prompt: str = Field(default="", max_length=10000)
    model: Optional[str] = Field(default="DeepSeek V4 Pro", max_length=50)
    tags: Optional[str] = Field(default="", max_length=500)
    variables: Optional[str] = Field(default="", max_length=500)

class PromptDeployRequest(BaseModel):
    prompt_id: int = Field(..., ge=1)
    system_prompt: str = Field(..., max_length=10000)
    user_prompt: str = Field(..., max_length=10000)
    model: str = Field(default="deepseek-v4-pro", max_length=50)
    variables: dict = Field(default={})


# ═══════════════════════════════════════
# Admin
# ═══════════════════════════════════════

class AdminUserUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    role: Optional[str] = Field(default=None, max_length=50)

class ApiKeyGenerateRequest(BaseModel):
    name: Optional[str] = Field(default="Admin Generated", max_length=100)
    plan: Optional[str] = Field(default="pro", max_length=50)


# ═══════════════════════════════════════
# Validation helper for Flask routes
# ═══════════════════════════════════════

from functools import wraps
from flask import request, jsonify

def validate(schema_class):
    """Decorator: validate Flask request JSON body against a Pydantic schema"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                data = request.get_json(silent=True) or {}
                validated = schema_class(**data)
                # Inject validated data into request
                request.validated = validated
                return f(*args, **kwargs)
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "message": f"输入校验失败: {str(e)}",
                    "validation_error": True
                }), 422
        return wrapper
    return decorator
