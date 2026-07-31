"""E2E集成测试: 全链路功能验证 + 边界条件 + 并发"""
import json, secrets, time, threading
from pathlib import Path
import sys; sys.path.insert(0, str(Path(__file__).parent.parent))


class TestE2EPipeline:
    """全链路: 租户→生产→分发→发布→通知"""

    def test_full_pipeline(self):
        # Step 1: 创建租户
        from tenant_service import create_tenant, check_quota, get_client_dashboard
        t = create_tenant("E2E测试装企", ["厦门"], "pro", "E2E Co")
        tid = t["id"]
        assert t["plan"] == "pro"

        # Step 2: 配额检查
        q = check_quota(tid)
        assert q["ok"] is True
        assert q["remaining"] == 150

        # Step 3: 记录用量
        from tenant_service import record_usage
        r = record_usage(tid, "article", "E2E测试话题")
        assert r["ok"] is True

        # Step 4: 账号矩阵
        from tenant_service import get_account_matrix
        m = get_account_matrix(tid)
        assert m["total_accounts"] >= 3  # pro: 1 city × 5 accounts

        # Step 5: 内容分发
        from content_scheduler import execute_distribution, get_stats, get_calendar
        d = execute_distribution(tid, "E2E测试分发", "article")
        assert d["ok"] is True
        assert d["total_distributions"] >= 3

        # Step 6: 队列统计
        s = get_stats(tid)
        assert s["queued"] + s["scheduled"] >= 3

        # Step 7: 日历
        c = get_calendar(tid, 7)
        assert len(c["calendar"]) == 7

        # Step 8: 仪表盘
        dash = get_client_dashboard(tid)
        assert dash["tenant"] == "E2E测试装企"

        # Step 9: 通知
        from notifications import notify, get_notifications, get_unread_count
        notify(tid, "content", "E2E测试", "全链路验证通过")
        ns = get_notifications(tid)
        assert len(ns) >= 1
        assert get_unread_count(tid) >= 1

        return True


class TestBillingAccuracy:
    """计费准确性: 配额·Token·超额"""

    def test_quota_exhaustion(self):
        from tenant_service import create_tenant, check_quota, record_usage
        t = create_tenant("计费测试", ["厦门"], "starter", "Bill Co")
        tid = t["id"]

        # 消耗配额
        for i in range(50):  # starter plan limit is 50
            record_usage(tid, "article", f"文章{i}")
        q = check_quota(tid)
        assert q["used"] == 50
        assert q["remaining"] == 0
        assert q["status"] == "exceeded"


class TestDistributionFormats:
    """分发格式化: 4平台适配"""

    def test_all_platforms_format(self):
        from content_scheduler import format_for_platform
        for platform in ["xiaohongshu", "douyin", "wechat", "shipinhao"]:
            f = format_for_platform({
                "topic": f"测试{platform}", "account": "测试号",
                "tenant_id": "zq-test-format"
            }, platform)
            assert f["platform"] != ""
            assert f["max_chars"] > 0
            assert Path(f["saved_to"]).exists()


class TestConcurrency:
    """并发安全: 多线程租户操作"""

    def test_concurrent_tenant_ops(self):
        from tenant_service import create_tenant, record_usage, check_quota
        errors = []
        results = []

        def worker(i):
            try:
                t = create_tenant(f"并发测试{i}", ["厦门"], "starter", "C")
                tid = t["id"]
                for j in range(5):
                    record_usage(tid, "article", f"文章{j}")
                q = check_quota(tid)
                results.append({"tid": tid, "used": q["used"]})
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads: t.start()
        for t in threads: t.join()

        assert len(errors) == 0, f"Concurrency errors: {errors}"
        assert len(results) == 5


class TestErrorHandling:
    """错误处理: 无效输入·404·边界"""

    def test_invalid_tenant(self):
        from tenant_service import get_tenant, check_quota
        assert get_tenant("zq-nonexistent") is None
        q = check_quota("zq-nonexistent")
        assert q["ok"] is False

    def test_invalid_plan(self):
        from tenant_service import get_plan
        p = get_plan("nonexistent")
        assert p["name"] == "入门版"  # defaults to starter

    def test_empty_distribution(self):
        from content_scheduler import execute_distribution
        d = execute_distribution("zq-nonexistent", "测试", "article")
        assert d["ok"] is False  # nonexistent tenant can't distribute

    def test_quota_guard(self):
        from tenant_service import create_tenant, check_quota, record_usage
        t = create_tenant("守卫测试", ["厦门"], "starter", "G")
        tid = t["id"]
        for i in range(50):
            record_usage(tid, "article", f"文{i}")
        q = check_quota(tid)
        # Quota exhausted
        assert q["status"] == "exceeded"


class TestNotificationsFlow:
    """通知完整流程"""

    def test_notification_lifecycle(self):
        from notifications import notify, get_notifications, get_unread_count, mark_read
        tid = f"zq-notify-{secrets.token_hex(4)}"

        # 发通知
        notify(tid, "content", "测试标题", "测试正文", "info")
        notify(tid, "quota", "配额预警", "85%", "warning")
        notify(tid, "system", "系统消息", "更新完成", "success")

        # 查未读
        assert get_unread_count(tid) == 3

        # 查列表
        ns = get_notifications(tid, limit=10)
        assert len(ns) == 3

        # 标记已读
        mark_read(tid)
        assert get_unread_count(tid) == 0


class TestPaymentFlow:
    """支付完整流程"""

    def test_payment_create_confirm(self):
        from payment_orders import create_order, confirm_payment, get_payment_stats, get_tenant_orders
        tid = f"zq-pay-{secrets.token_hex(4)}"

        o = create_order(tid, "pro")
        assert o["ok"] is True
        assert o["order"]["status"] == "pending"
        assert o["order"]["amount"] == 999

        c = confirm_payment(o["order"]["id"])
        assert c["ok"] is True
        assert c["order"]["status"] == "paid"

        orders = get_tenant_orders(tid)
        assert len(orders) == 1

        stats = get_payment_stats()
        assert stats["revenue"] >= 999
