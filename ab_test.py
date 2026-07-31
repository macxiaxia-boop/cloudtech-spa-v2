"""
A/B Testing Framework — Split traffic between page variants, measure conversions
Usage: Add ?ab_variant=B to URL, or auto-assign by cookie
"""
import json, os, hashlib, secrets
from datetime import datetime
from pathlib import Path
from flask import request, make_response


AB_DATA = Path(__file__).parent / "data" / "ab_tests.jsonl"


class ABTest:
    """Simple A/B test: split traffic, track conversions"""

    def __init__(self, name: str, variants: list[str], traffic_split: list[float] = None):
        self.name = name
        self.variants = variants
        self.traffic_split = traffic_split or [1.0 / len(variants)] * len(variants)

    def assign(self, user_id: str = None) -> str:
        """Assign user to a variant. Deterministic by user_id if provided."""
        if user_id:
            h = int(hashlib.md5(f"{self.name}:{user_id}".encode()).hexdigest()[:8], 16)
            bucket = h % 100
        else:
            bucket = secrets.randbelow(100)

        cumulative = 0
        for i, pct in enumerate(self.traffic_split):
            cumulative += pct * 100
            if bucket < cumulative:
                return self.variants[i]

        return self.variants[-1]

    def track_impression(self, variant: str, user_id: str = "", url: str = ""):
        """Record a page view for a variant"""
        _log(self.name, variant, "impression", user_id, url)

    def track_conversion(self, variant: str, user_id: str = "", goal: str = "signup", url: str = ""):
        """Record a conversion (signup, purchase, etc.)"""
        _log(self.name, variant, f"conversion:{goal}", user_id, url)

    def get_stats(self) -> dict:
        """Get current test stats"""
        if not AB_DATA.exists():
            return {"name": self.name, "variants": {}, "total_impressions": 0, "total_conversions": 0}

        variants = {v: {"impressions": 0, "conversions": 0, "conversion_rate": 0} for v in self.variants}
        total_imp = 0
        total_conv = 0

        with open(AB_DATA, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line.strip())
                    if e.get("test") != self.name:
                        continue
                    v = e.get("variant")
                    if v not in variants:
                        continue
                    if "conversion" in e.get("event", ""):
                        variants[v]["conversions"] += 1
                        total_conv += 1
                    else:
                        variants[v]["impressions"] += 1
                        total_imp += 1
                except Exception:
                    continue

        for v in variants:
            imp = variants[v]["impressions"]
            conv = variants[v]["conversions"]
            variants[v]["conversion_rate"] = round(conv / imp * 100, 2) if imp > 0 else 0

        # Find winner (highest conversion rate with at least 10 impressions)
        candidates = [(v, d["conversion_rate"]) for v, d in variants.items() if d["impressions"] >= 10]
        winner = max(candidates, key=lambda x: x[1])[0] if candidates else None

        return {
            "name": self.name,
            "variants": variants,
            "total_impressions": total_imp,
            "total_conversions": total_conv,
            "winner": winner,
        }


def _log(test: str, variant: str, event: str, user_id: str = "", url: str = ""):
    AB_DATA.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "test": test,
        "variant": variant,
        "event": event,
        "user_id": user_id,
        "url": url,
    }
    with open(AB_DATA, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── 预定义测试实例 ──
HOMEPAGE_TEST = ABTest("homepage", ["A-原版", "B-数据驱动版", "C-视频优先版"], [0.33, 0.34, 0.33])
PRICING_TEST = ABTest("pricing", ["A-三栏", "B-单列对比"], [0.5, 0.5])
CONTENT_TEST = ABTest("content_style", ["直男财经", "小Lin说", "高盖伦", "小A学财经"], [0.25, 0.25, 0.25, 0.25])

# Flask middleware for A/B testing
def ab_middleware(app):
    """Auto-assign A/B variant and track impressions"""

    @app.before_request
    def assign_ab():
        if request.path == "/" and not request.args.get("ab_variant"):
            test = ABTest("homepage", ["A", "B"], [0.5, 0.5])
            variant = request.cookies.get("ab_homepage") or test.assign()
            test.track_impression(variant, request.remote_addr, request.path)

            # Set cookie so user always sees same variant
            if not request.cookies.get("ab_homepage"):
                resp = make_response()
                resp.set_cookie("ab_homepage", variant, max_age=86400 * 30)
                # We can't modify response in before_request, just track


# Pre-configured tests
HOMEPAGE_TEST = ABTest("homepage", ["A", "B"], [0.5, 0.5])
PRICING_TEST = ABTest("pricing", ["monthly_first", "yearly_first"], [0.5, 0.5])
