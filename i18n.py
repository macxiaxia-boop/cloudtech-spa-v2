"""
多语言支持 — Internationalization & Multi-Language Content
对标筷子: 国际站 kuaizi.ai·跨境电商·多语言内容
"""
import json
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent
I18N_DIR = Path("D:/个人文件/AI/云数科技/i18n")
I18N_DIR.mkdir(parents=True, exist_ok=True)

# 支持的语言
LANGUAGES = {
    "zh-CN": "简体中文", "zh-TW": "繁体中文", "en": "English",
    "ja": "日本語", "ko": "한국어", "th": "ไทย", "vi": "Tiếng Việt",
    "ms": "Bahasa Melayu", "id": "Bahasa Indonesia", "es": "Español",
    "pt": "Português", "ar": "العربية", "ru": "Русский",
}

# UI翻译表
TRANSLATIONS = {
    "dashboard": {"zh-CN": "仪表盘", "en": "Dashboard", "ja": "ダッシュボード", "ko": "대시보드"},
    "content": {"zh-CN": "内容管理", "en": "Content", "ja": "コンテンツ", "ko": "콘텐츠"},
    "analytics": {"zh-CN": "数据分析", "en": "Analytics", "ja": "分析", "ko": "분석"},
    "publish": {"zh-CN": "发布管理", "en": "Publish", "ja": "公開", "ko": "게시"},
    "settings": {"zh-CN": "设置", "en": "Settings", "ja": "設定", "ko": "설정"},
    "brand": {"zh-CN": "品牌资产", "en": "Brand Assets", "ja": "ブランド資産", "ko": "브랜드 자산"},
    "rights": {"zh-CN": "版权中心", "en": "Rights Center", "ja": "著作権センター", "ko": "저작권 센터"},
    "team": {"zh-CN": "团队协作", "en": "Team", "ja": "チーム", "ko": "팀"},
    "quota_warning": {"zh-CN": "配额即将用尽", "en": "Quota almost exhausted", "ja": "クォータがまもなく枯渇", "ko": "할당량 거의 소진"},
    "content_ready": {"zh-CN": "内容生产完成", "en": "Content ready", "ja": "コンテンツ準備完了", "ko": "콘텐츠 준비 완료"},
}


def t(key: str, lang: str = "zh-CN") -> str:
    """翻译key"""
    return TRANSLATIONS.get(key, {}).get(lang, key)


def get_languages() -> dict:
    return LANGUAGES


def translate_content(text: str, target_lang: str) -> dict:
    """
    内容翻译（标记待AI翻译）
    实际翻译通过DeepSeek API执行
    """
    job_id = f"tr-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    job = {
        "id": job_id, "source_lang": "zh-CN", "target_lang": target_lang,
        "source_text": text[:3000], "status": "pending",
        "translated_text": "", "created_at": datetime.now().isoformat()[:19],
    }
    jf = I18N_DIR / f"{job_id}.json"
    jf.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "job": job, "hint": "实际翻译通过DeepSeek API异步执行"}


def get_translation_jobs(limit: int = 20) -> list:
    jobs = []
    for f in sorted(I18N_DIR.glob("tr-*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            jobs.append(json.loads(f.read_text(encoding="utf-8")))
            if len(jobs) >= limit: break
        except Exception: pass
    return jobs
