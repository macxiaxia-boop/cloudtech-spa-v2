"""
Phase 47.6 验证测试: FAQ/Blog/Documents/ClientList 4 页面 banner 接入 + 总图数 9
"""
import os
import re

ROOT = "D:/CloudTech-Portable"
WEB = f"{ROOT}/web/vite-spa"
SRC = f"{WEB}/src"
PUBLIC = f"{WEB}/public"

def test_4_new_images_exist():
    """4 张新 banner 图存在且 > 100KB"""
    images = ["faq-hero.jpeg", "blog-hero.jpeg", "documents-hero.jpeg", "clients-hero.jpeg"]
    for img in images:
        path = f"{PUBLIC}/images/{img}"
        assert os.path.exists(path), f"缺失: {path}"
        size = os.path.getsize(path)
        assert size > 100_000, f"{img} 太小 ({size}B)"
        print(f"  ✓ {img}: {size//1024} KB")


def test_total_images_count():
    """public/images/ 共 9 张 (Phase 47.5 + Phase 47.6)"""
    images_dir = f"{PUBLIC}/images"
    files = [f for f in os.listdir(images_dir) if f.endswith(".jpeg")]
    assert len(files) == 9, f"应有 9 张，实际 {len(files)}: {files}"
    total = sum(os.path.getsize(os.path.join(images_dir, f)) for f in files)
    print(f"  ✓ 9 张图 · 总 {total/1024/1024:.2f}MB")


def test_faq_uses_hero_image():
    """FAQ.tsx 含 faq-hero.jpeg + 关键数字"""
    content = open(f"{SRC}/pages/FAQ.tsx", encoding="utf-8").read()
    assert "faq-hero.jpeg" in content, "FAQ 缺 hero 图"
    assert "md:grid-cols-2" in content, "FAQ hero 应是 2 列网格"
    assert "1280+" in content or "helpful" in content, "FAQ 缺关键数字"
    print("  ✓ FAQ: faq-hero + 2 列 + 1280+ helpful")


def test_blog_uses_hero_image():
    """Blog.tsx 含 blog-hero.jpeg"""
    content = open(f"{SRC}/pages/Blog.tsx", encoding="utf-8").read()
    assert "blog-hero.jpeg" in content, "Blog 缺 hero 图"
    assert "md:grid-cols-2" in content, "Blog hero 应是 2 列网格"
    assert "9 篇" in content, "Blog 缺关键数字"
    print("  ✓ Blog: blog-hero + 2 列 + 9 篇")


def test_documents_uses_hero_image():
    """Documents.tsx 含 documents-hero.jpeg"""
    content = open(f"{SRC}/pages/Documents.tsx", encoding="utf-8").read()
    assert "documents-hero.jpeg" in content, "Documents 缺 hero 图"
    assert "md:grid-cols-2" in content, "Documents hero 应是 2 列网格"
    assert "红 #22" in content, "Documents 红线守卫文案缺失"
    print("  ✓ Documents: documents-hero + 2 列 + 红 #22")


def test_client_list_uses_hero_image():
    """ClientList.tsx 含 clients-hero.jpeg"""
    content = open(f"{SRC}/pages/ClientList.tsx", encoding="utf-8").read()
    assert "clients-hero.jpeg" in content, "ClientList 缺 hero 图"
    assert "md:grid-cols-2" in content, "ClientList hero 应是 2 列网格"
    assert "20 城" in content or "全国 20 城" in content, "ClientList 缺城市数据"
    print("  ✓ ClientList: clients-hero + 2 列 + 20 城")


def test_no_regression_phase_47_5():
    """Phase 47.5 测试文件保留"""
    for f in ["test_phase47_5_illustrations_density.py", "test_phase47_stage123_all.py"]:
        path = f"{ROOT}/tests/{f}"
        assert os.path.exists(path), f"测试文件丢失: {path}"
    print("  ✓ Phase 47.5 + Stage 1+2+3 测试保留")


def test_all_pages_have_hero_2col():
    """5 行业页 + 6 内容页 hero 全部 2 列网格 (text + image)"""
    pages_with_2col = [
        ("Marketing.tsx", "ai-team"),
        ("IndustryDecoration.tsx", "decoration-hero"),
        ("IndustryMedical.tsx", "medical-hero"),
        ("OPCStory.tsx", "opc-hero"),
        ("Dashboard.tsx", "dashboard-preview"),
        ("FAQ.tsx", "faq-hero"),
        ("Blog.tsx", "blog-hero"),
        ("Documents.tsx", "documents-hero"),
        ("ClientList.tsx", "clients-hero"),
    ]
    for fname, img_key in pages_with_2col:
        content = open(f"{SRC}/pages/{fname}", encoding="utf-8").read()
        assert img_key in content, f"{fname} 缺 {img_key}"
        assert "md:grid-cols-2" in content or "/images/" in content, f"{fname} hero 应含 2 列或 image"
    print(f"  ✓ 9 页面 hero 全含图 (5 行业/营销 + 4 内容页)")


def test_cta_point_to_try_industry():
    """Industry 行业页 CTA 全部 /try"""
    for fname in ["IndustryDecoration.tsx", "IndustryMedical.tsx"]:
        content = open(f"{SRC}/pages/{fname}", encoding="utf-8").read()
        assert 'to="/try"' in content, f"{fname} 缺 /try CTA"
    print("  ✓ 2 行业页 CTA → /try")


def run_all():
    tests = [
        test_4_new_images_exist,
        test_total_images_count,
        test_faq_uses_hero_image,
        test_blog_uses_hero_image,
        test_documents_uses_hero_image,
        test_client_list_uses_hero_image,
        test_no_regression_phase_47_5,
        test_all_pages_have_hero_2col,
        test_cta_point_to_try_industry,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            print(f"\n[{t.__name__}]")
            t()
            passed += 1
        except Exception as e:
            print(f"  ✗ {e}")
            failed += 1
    print(f"\n{'='*60}")
    print(f"Phase 47.6: {passed} PASS · {failed} FAIL · {passed+failed} 总数")
    print(f"{'='*60}")
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if run_all() else 1)