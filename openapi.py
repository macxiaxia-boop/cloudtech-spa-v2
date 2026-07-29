"""
CloudTech v2.1 — OpenAPI 3.0 Specification Generator
Generates API documentation from Pydantic schemas + route metadata
"""
import json
from pathlib import Path
from typing import Any

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "CloudTech API",
        "version": "2.1.0",
        "description": "云数科技 AI数字营销中台 — 内容创作·GEO优化·提示词工程·二创管线·装企引擎",
        "contact": {"name": "CloudTech Team", "email": "admin@cloudtech.com"},
    },
    "servers": [
        {"url": "http://localhost:5099", "description": "Local development"},
    ],
    "tags": [
        {"name": "System", "description": "系统健康检查"},
        {"name": "Auth", "description": "认证与授权"},
        {"name": "Content Creation", "description": "内容创作引擎 — 4大创作者·6种内容形式"},
        {"name": "Repurpose", "description": "内容二创管线"},
        {"name": "Zhuangqi", "description": "装企内容引擎"},
        {"name": "GEO", "description": "GEO搜索优化"},
        {"name": "Prompts", "description": "AI提示词工程"},
        {"name": "Social", "description": "社交媒体采集与趋势情报"},
        {"name": "Admin", "description": "管理后台 (需要认证)"},
    ],
    "paths": {
        "/health": {
            "get": {
                "tags": ["System"],
                "summary": "Health check",
                "responses": {"200": {"description": "OK"}},
            }
        },
        "/api/system/status": {
            "get": {
                "tags": ["System"],
                "summary": "System service status",
                "responses": {"200": {"description": "Service statuses"}},
            }
        },
        "/api/auth/login": {
            "post": {
                "tags": ["Auth"],
                "summary": "User login",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {
                        "schema": {"$ref": "#/components/schemas/LoginRequest"}
                    }}
                },
                "responses": {
                    "200": {"description": "JWT token"},
                    "401": {"description": "Invalid credentials"},
                    "422": {"description": "Validation error"},
                },
            }
        },
        "/api/auth/register": {
            "post": {
                "tags": ["Auth"],
                "summary": "User registration",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {
                        "schema": {"$ref": "#/components/schemas/RegisterRequest"}
                    }}
                },
                "responses": {"200": {"description": "User created"}, "422": {"description": "Validation error"}},
            }
        },
        "/api/create/styles": {
            "get": {
                "tags": ["Content Creation"],
                "summary": "List creator styles (4 major creators)",
                "responses": {"200": {"description": "Creator styles with platforms"}},
            }
        },
        "/api/create/forms": {
            "get": {
                "tags": ["Content Creation"],
                "summary": "List content forms (6 types) + hook types + story formulas",
                "responses": {"200": {"description": "Content form definitions"}},
            }
        },
        "/api/create/topic-discovery": {
            "post": {
                "tags": ["Content Creation"],
                "summary": "Topic discovery by domain + creator styles",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {
                        "schema": {"$ref": "#/components/schemas/TopicDiscoveryRequest"}
                    }}
                },
                "responses": {"200": {"description": "Topic briefs"}, "422": {"description": "Validation error"}},
            }
        },
        "/api/create/generate-v2": {
            "post": {
                "tags": ["Content Creation"],
                "summary": "AI content generation (3-phase: research→write→de-AI check)",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {
                        "schema": {"$ref": "#/components/schemas/GenerateV2Request"}
                    }}
                },
                "responses": {"200": {"description": "Generated content with research + de-AI report"}},
            }
        },
        "/api/create/multi-platform": {
            "post": {
                "tags": ["Content Creation"],
                "summary": "One topic → multi-platform adaptation",
                "responses": {"200": {"description": "Platform-specific versions"}},
            }
        },
        "/api/create/style-clone": {
            "post": {
                "tags": ["Content Creation"],
                "summary": "Extract style DNA from reference text",
                "responses": {"200": {"description": "Style DNA analysis"}},
            }
        },
        "/api/create/deai-check": {
            "post": {
                "tags": ["Content Creation"],
                "summary": "5-dimension de-AI quality check",
                "responses": {"200": {"description": "De-AI report"}},
            }
        },
        "/api/repurpose/extract": {
            "post": {
                "tags": ["Repurpose"],
                "summary": "Extract content + images from URL",
                "responses": {"200": {"description": "Extracted content with image metadata"}},
            }
        },
        "/api/repurpose/rewrite": {
            "post": {
                "tags": ["Repurpose"],
                "summary": "AI rewrite with style selection",
                "responses": {"200": {"description": "Rewritten content"}},
            }
        },
        "/api/zhuangqi/formats": {
            "get": {
                "tags": ["Zhuangqi"],
                "summary": "List decoration content formats (8 types)",
                "responses": {"200": {"description": "Content formats"}},
            }
        },
        "/api/zhuangqi/scenes": {
            "get": {
                "tags": ["Zhuangqi"],
                "summary": "List industry scenes (18 categories × 222 keywords)",
                "responses": {"200": {"description": "Scene definitions"}},
            }
        },
        "/api/zhuangqi/brief": {
            "post": {
                "tags": ["Zhuangqi"],
                "summary": "Generate content brief",
                "responses": {"200": {"description": "Content brief"}},
            }
        },
        "/api/zhuangqi/week-plan": {
            "post": {
                "tags": ["Zhuangqi"],
                "summary": "Generate 7-day content plan",
                "responses": {"200": {"description": "Weekly plan"}},
            }
        },
        "/api/geo/keyword-research": {
            "post": {
                "tags": ["GEO"],
                "summary": "GEO keyword intent analysis",
                "responses": {"200": {"description": "Keyword analysis"}},
            }
        },
        "/api/geo/rank-check": {
            "post": {
                "tags": ["GEO"],
                "summary": "Multi-platform rank check (DeepSeek/豆包/Kimi)",
                "responses": {"200": {"description": "Rank results"}},
            }
        },
        "/api/geo/content-generate": {
            "post": {
                "tags": ["GEO"],
                "summary": "Generate GEO-optimized content",
                "responses": {"200": {"description": "GEO content"}},
            }
        },
        "/api/prompts/list": {"get": {"tags": ["Prompts"], "summary": "List saved prompts"}},
        "/api/prompts/create": {"post": {"tags": ["Prompts"], "summary": "Create prompt", "responses": {"200": {"description": "Prompt created"}}}},
        "/api/prompts/generate": {"post": {"tags": ["Prompts"], "summary": "AI generate prompt", "responses": {"200": {"description": "Generated prompt pair"}}}},
        "/api/prompts/deploy": {"post": {"tags": ["Prompts"], "summary": "Deploy prompt with variables", "responses": {"200": {"description": "Execution result"}}}},
        "/api/prompts/templates": {"get": {"tags": ["Prompts"], "summary": "List preset templates"}},
        "/api/zhuangqi/social/search": {
            "post": {
                "tags": ["Social"],
                "summary": "Tavily social search",
                "responses": {"200": {"description": "Social search results"}},
            }
        },
        "/api/admin/dashboard": {
            "get": {
                "tags": ["Admin"],
                "summary": "Admin dashboard stats [Auth required]",
                "security": [{"AdminToken": []}],
                "responses": {"200": {"description": "Dashboard stats"}, "401": {"description": "Unauthorized"}},
            }
        },
        "/api/admin/users": {
            "get": {
                "tags": ["Admin"],
                "summary": "List/search users [Auth required]",
                "security": [{"AdminToken": []}],
                "parameters": [
                    {"name": "search", "in": "query", "schema": {"type": "string"}},
                    {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 20}},
                ],
                "responses": {"200": {"description": "User list"}},
            }
        },
    },
    "components": {
        "securitySchemes": {
            "AdminToken": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Admin-Token",
                "description": "JWT token from /api/auth/login"
            }
        },
        "schemas": {
            "LoginRequest": {
                "type": "object",
                "required": ["email", "password"],
                "properties": {
                    "email": {"type": "string", "format": "email", "minLength": 5, "example": "admin@cloudtech.com"},
                    "password": {"type": "string", "format": "password", "minLength": 6, "example": "admin123"},
                },
            },
            "RegisterRequest": {
                "type": "object",
                "required": ["email", "password", "name"],
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "password": {"type": "string", "minLength": 6},
                    "name": {"type": "string", "minLength": 1},
                    "company": {"type": "string"},
                    "plan": {"type": "string", "enum": ["starter", "pro", "enterprise"]},
                },
            },
            "TopicDiscoveryRequest": {
                "type": "object",
                "required": ["domain", "creators"],
                "properties": {
                    "domain": {"type": "string", "example": "装修设计"},
                    "creators": {"type": "array", "items": {"type": "string", "enum": ["zhinan", "xiaolin", "gaogailun", "xiaoa"]}, "minItems": 1},
                    "count": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                },
            },
            "GenerateV2Request": {
                "type": "object",
                "required": ["topic", "content_form", "creator", "platform"],
                "properties": {
                    "topic": {"type": "string", "minLength": 1},
                    "content_form": {"type": "string", "enum": ["voiceover", "persona", "storytelling", "mashup", "article", "short_video"]},
                    "creator": {"type": "string", "enum": ["zhinan", "xiaolin", "gaogailun", "xiaoa"]},
                    "platform": {"type": "string", "enum": ["douyin", "xiaohongshu", "wechat", "zhihu", "bilibili", "pengyouquan"]},
                    "word_count": {"type": "integer", "minimum": 50, "maximum": 10000, "default": 1500},
                    "hook_type": {"type": "string", "enum": ["H1", "H2", "H3", "H4", "H5", "H6"]},
                    "story_formula": {"type": "string", "enum": ["wealth", "cognitive", "curiosity", "ranking"]},
                    "expression": {"type": "string", "enum": ["bestie", "scholar", "business"]},
                    "extra": {"type": "string"},
                },
            },
        },
    },
    "security": [],
}


def get_spec() -> dict:
    """Return the full OpenAPI specification"""
    return OPENAPI_SPEC


def get_spec_json() -> str:
    """Return OpenAPI spec as pretty-printed JSON"""
    return json.dumps(OPENAPI_SPEC, ensure_ascii=False, indent=2)
