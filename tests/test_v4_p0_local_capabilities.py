"""Local capability proof: no fake OCR, metrics or author catalog."""
from PIL import Image
from adapters.ocr import LocalOCREngine
from adapters.search import LocalAuthorSearch
from adapters.metrics import LocalMetrics


def test_ocr_cannot_read_outside_approved_upload_root(tmp_path, monkeypatch):
    root = tmp_path / "approved"
    root.mkdir()
    image = tmp_path / "secrets.png"
    Image.new("RGB", (20, 20), color="white").save(image)
    monkeypatch.setenv("CLOUDTECH_OCR_INPUT_ROOT", str(root))
    result = LocalOCREngine().recognize(str(image))
    assert result["status"] == "blocked"
    assert result["error_code"] == "OCR_PATH_OUTSIDE_ALLOWED_ROOT"
    assert "full_text" not in result


def test_ocr_pdf_is_explicitly_not_supported(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUDTECH_OCR_INPUT_ROOT", str(tmp_path))
    pdf = tmp_path / "invoice.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake local header for format gate")
    result = LocalOCREngine().recognize(str(pdf))
    assert result["error_code"] == "OCR_UNSUPPORTED_FORMAT"
    assert result["mock"] is False


def test_local_metrics_deduplicates_work_ids_not_view_counts():
    source = [
        {"work_id": "one", "author_id": "u", "view_count": 10,
         "like_count": 1, "comment_count": 2, "share_count": 0},
        {"work_id": "one", "author_id": "u", "view_count": 10,
         "like_count": 1, "comment_count": 2, "share_count": 0},
        {"work_id": "two", "author_id": "u", "view_count": 40,
         "like_count": 3, "comment_count": 0, "share_count": 1},
    ]
    result = LocalMetrics().fetch_videos("u", source)
    assert result["total_videos"] == 2
    assert result["total_views"] == 50
    assert result["total_likes"] == 4
    assert result["engagement_rate"] == 7 / 50
    assert result["mock"] is False


def test_invalid_metrics_never_silently_counted():
    source = [{"work_id": "bad", "author_id": "u", "view_count": -10,
               "like_count": 1, "comment_count": 0, "share_count": 0}]
    try:
        LocalMetrics().fetch_videos("u", source)
        assert False, "negative views must be invalid"
    except ValueError as err:
        assert "view_count" in str(err)


def test_local_author_search_respects_platform_and_source_data():
    catalog = [
        {"author_id": "a", "name": "装修好帮手", "platform": "douyin"},
        {"author_id": "b", "name": "装修案例", "platform": "xiaohongshu"},
        {"author_id": "c", "name": "汽车博主", "platform": "douyin"},
    ]
    result = LocalAuthorSearch().search_authors(["装修"], platform="douyin", catalog=catalog)
    assert result["total"] == 1
    assert result["items"][0]["author_id"] == "a"
    assert result["mock"] is False
    assert result["provider_called"] is False
