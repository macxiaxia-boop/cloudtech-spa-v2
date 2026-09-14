"""
Cloud Python SDK
================
Phase 48.D87 · Python 客户端 SDK（Cloud API 封装）
基于 OpenAPI 3.0 规范自动生成 · 15 个端点全覆盖
红线 #22：实际使用需用户拍板（API key 申请 + 调用额度）

安装：
    pip install requests

使用示例：
    from cloud_sdk import CloudClient

    client = CloudClient(
        base_url="https://api.cloud.example.com",
        access_token="your_jwt_token"
    )

    # 登录
    auth = client.login("user@example.com", "password123")
    client.set_token(auth.access_token)

    # 生成内容
    result = client.generate_content(
        topic="OPC 模式适合什么规模的公司",
        style_id="hermes_governance",
        form_id="wechat_article"
    )
    print(result.content)

错误处理：
    try:
        result = client.generate_content(...)
    except CloudAuthError:
        # 重新登录
        pass
    except CloudQuotaError:
        # 配额超限 · 升级套餐
        pass
"""

import time
import requests
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# ============ 数据模型 ============

@dataclass
class User:
    id: str
    email: str
    role: str


@dataclass
class LoginResponse:
    access_token: str
    refresh_token: str
    expires_in: int
    user: User


@dataclass
class Style:
    id: str
    name: str
    description: str
    emoji: str


@dataclass
class GenerateResponse:
    content: str
    tokens_used: int
    style_id: str
    form_id: str
    redline_violations: List[str] = field(default_factory=list)


# ============ 异常 ============

class CloudError(Exception):
    """Cloud SDK 基础异常"""
    def __init__(self, message: str, code: int = 0, request_id: str = ""):
        super().__init__(message)
        self.code = code
        self.request_id = request_id


class CloudAuthError(CloudError):
    """鉴权失败 (401)"""
    pass


class CloudForbiddenError(CloudError):
    """无权限 (403)"""
    pass


class CloudQuotaError(CloudError):
    """配额超限 (402)"""
    pass


class CloudNotFoundError(CloudError):
    """资源不存在 (404)"""
    pass


# ============ 客户端 ============

class CloudClient:
    def __init__(
        self,
        base_url: str = "https://api.cloud.example.com",
        access_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

    def set_token(self, access_token: str) -> None:
        """设置/更新访问令牌"""
        self.access_token = access_token

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        auth_required: bool = False,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if auth_required:
            if not self.access_token:
                raise CloudAuthError("需要先登录或设置 access_token")
            headers["Authorization"] = f"Bearer {self.access_token}"

        last_error = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    json=json,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
                if resp.status_code == 401:
                    raise CloudAuthError(resp.text, code=401, request_id=resp.headers.get("X-Request-ID", ""))
                if resp.status_code == 402:
                    raise CloudQuotaError(resp.text, code=402, request_id=resp.headers.get("X-Request-ID", ""))
                if resp.status_code == 403:
                    raise CloudForbiddenError(resp.text, code=403, request_id=resp.headers.get("X-Request-ID", ""))
                if resp.status_code == 404:
                    raise CloudNotFoundError(resp.text, code=404, request_id=resp.headers.get("X-Request-ID", ""))
                resp.raise_for_status()
                return resp.json()
            except (requests.ConnectionError, requests.Timeout) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                raise CloudError(f"网络错误: {e}") from e
        raise CloudError(f"重试 {self.max_retries} 次后失败: {last_error}")

    # ===== Auth =====
    def login(self, email: str, password: str) -> LoginResponse:
        data = self._request("POST", "/api/v2/auth/login", json={"email": email, "password": password})
        auth = LoginResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data["expires_in"],
            user=User(**data["user"]),
        )
        self.set_token(auth.access_token)
        return auth

    # ===== System =====
    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v2/health")

    def metrics(self) -> str:
        return self._request("GET", "/api/v2/metrics")

    # ===== Content Creation =====
    def list_styles(self) -> List[Style]:
        data = self._request("GET", "/api/v2/create/styles")
        return [Style(**s) for s in data]

    def list_forms(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/api/v2/create/forms")

    def generate_content(
        self,
        topic: str,
        style_id: str,
        form_id: str,
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ) -> GenerateResponse:
        data = self._request(
            "POST",
            "/api/v2/create/generate",
            json={
                "topic": topic,
                "style_id": style_id,
                "form_id": form_id,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        return GenerateResponse(
            content=data["content"],
            tokens_used=data["tokens_used"],
            style_id=data["style_id"],
            form_id=data["form_id"],
            redline_violations=data.get("redline_violations", []),
        )

    def topic_discovery(
        self,
        industry: str,
        keywords: List[str],
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        return self._request(
            "POST",
            "/api/v2/create/topic-discovery",
            json={"industry": industry, "keywords": keywords, "max_results": max_results},
        )

    # ===== Repurpose =====
    def repurpose_extract(
        self,
        content: str,
        extract_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        extract_types = extract_types or ["title", "hook", "data", "case", "quote"]
        return self._request(
            "POST",
            "/api/v2/repurpose/extract",
            json={"content": content, "extract_types": extract_types},
        )

    def repurpose_rewrite(
        self,
        content: str,
        target_form: str,
        max_length: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload = {"content": content, "target_form": target_form}
        if max_length is not None:
            payload["max_length"] = max_length
        return self._request("POST", "/api/v2/repurpose/rewrite", json=payload)

    # ===== Admin =====
    def admin_dashboard(self) -> Dict[str, Any]:
        return self._request("GET", "/api/v2/admin/dashboard", auth_required=True)

    def admin_users(
        self,
        search: str = "",
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/api/v2/admin/users",
            params={"search": search, "page": page, "limit": limit},
            auth_required=True,
        )

    # ===== IM =====
    def im_chat(self, user_id: str, message: str, context: Optional[List[Dict]] = None) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/v2/im/chat",
            json={"user_id": user_id, "message": message, "context": context or []},
        )

    def im_wecom_send(self, user_id: str, message: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/v2/im/wecom/send",
            json={"user_id": user_id, "message": message},
        )


# ============ 便捷函数 ============

_default_client = None


def get_default_client() -> CloudClient:
    global _default_client
    if _default_client is None:
        _default_client = CloudClient()
    return _default_client


def quick_generate(topic: str, style_id: str = "hermes_governance", form_id: str = "wechat_article") -> str:
    """快速生成内容（使用默认客户端）"""
    client = get_default_client()
    result = client.generate_content(topic=topic, style_id=style_id, form_id=form_id)
    return result.content


__all__ = [
    "CloudClient",
    "LoginResponse",
    "Style",
    "GenerateResponse",
    "User",
    "CloudError",
    "CloudAuthError",
    "CloudForbiddenError",
    "CloudQuotaError",
    "CloudNotFoundError",
    "quick_generate",
    "get_default_client",
]
