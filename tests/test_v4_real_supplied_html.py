"""Real offline article extraction, no example body, network, or AI provider."""
import hashlib
from adapters.article.article_parser import parse_html
from workflows.v4.registry import OperationRegistry

HTML = (
    '<html><head><title>企业如何使用 AI</title></head>'
    '<body><h1>原文标题</h1>'
    '<p>第一段，客户自己提供的真实正文。</p>'
    '<p>第二段，用于验证跨段内容提取。</p>'
    '<script>window.secret="NEVER_OUTPUT"</script>'
    '<img src="https://example.com/a.png" alt="真实配图">'
    '<video src="https://example.com/demo.mp4"></video>'
    '</body></html>'
)

def test_extract_real_supplied_content_with_provenance():
    out = parse_html(HTML, "https://example.com/article")
    assert out["title"] == "企业如何使用 AI"
    assert "第一段" in out["text"] and "第二段" in out["text"]
    assert "NEVER_OUTPUT" not in out["text"]
    assert "企业如何使用 AI" not in out["text"]  # head <title> not article body
    assert out["content_sha256"] == hashlib.sha256(HTML.encode()).hexdigest()
    assert out["retrieval_policy"] == "supplied_html_only"
    assert out["mock"] is False
    assert out["images"][0]["license"] == "unknown_need_user_confirm"

def test_registered_article_html_parse_is_real():
    out = OperationRegistry().dispatch(
        "article.html_parse", {"html": HTML, "source_url": "https://example.com/a"})
    assert out["mock"] is False
    assert "客户自己提供" in out["text"]
    assert len(out["images"]) == 1
    assert len(out["videos"]) >= 1

def test_registered_media_extract_is_not_fabricated():
    out = OperationRegistry().dispatch("article.media_extract", {"html": HTML})
    assert out["mock"] is False
    assert out["images"][0]["url"] == "https://example.com/a.png"
    assert "text" not in out

def test_no_html_blocks_instead_of_generating_example_article():
    out = OperationRegistry().dispatch("article.html_parse", {"url": "https://example.com/unknown"})
    assert out["status"] == "blocked"
    assert out["error_code"] == "USER_HTML_REQUIRED"
    assert "text" not in out

def test_html_size_limit_is_enforced():
    try:
        parse_html("<p>" + "x" * 2_100_000 + "</p>")
        assert False, "size limit bypassed"
    except ValueError as e:
        assert "2MB" in str(e)

def test_url_mock_parser_forbidden_in_production(monkeypatch):
    from adapters.article.article_parser import parse
    monkeypatch.setenv("CLOUDTECH_ENV", "production")
    monkeypatch.setenv("CLOUDTECH_ALLOW_MOCK_ARTICLE", "1")
    try:
        parse("https://example.com/any-article")
        assert False, "fabricated article was allowed in production"
    except RuntimeError as error:
        assert "ARTICLE-MOCK-403" in str(error)


def test_authenticated_http_article_endpoint_preserves_tenant_and_no_network():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.v4 import router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    body = {"html": HTML, "source_url": "https://example.com/original"}
    assert client.post("/v4/article/extract-html", json=body).status_code == 422
    response = client.post("/v4/article/extract-html?tenant_id=tenant_a", json=body)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["tenant_id"] == "tenant_a"
    assert result["mock"] is False
    assert result["provider_called"] is False
    assert result["saved"] is False
    assert result["permission_status"] == "rights_unknown_need_user_confirm"
    assert result["content_sha256"] == hashlib.sha256(HTML.encode()).hexdigest()
