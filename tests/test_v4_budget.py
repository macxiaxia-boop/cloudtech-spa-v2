"""V4 budget 测试"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workflows.v4 import BudgetGate, CostClass, BudgetError


def test_reserve_and_settle():
    bg = BudgetGate()
    res = bg.reserve("t1", "r1", "n1", CostClass.METERED_MEDIA, 100, 1000)
    bg.settle(res.reservation_id, 100)
    assert bg.get_spent("t1") == 100
    print(f"[OK] reserve+settle → spent={bg.get_spent('t1')}")


def test_cap_exceeded():
    bg = BudgetGate()
    try:
        bg.reserve("t1", "r1", "n1", CostClass.METERED_MEDIA, 100, 50)
        assert False, "应抛超限"
    except BudgetError as e:
        print(f"[OK] cap_exceeded → {e}")


def test_release_on_failure():
    bg = BudgetGate()
    res = bg.reserve("t1", "r1", "n1", CostClass.METERED_MEDIA, 200, 1000)
    bg.release(res.reservation_id)
    assert bg.get_spent("t1") == 0
    print("[OK] release → not settled")


def test_double_settle_rejected():
    bg = BudgetGate()
    res = bg.reserve("t1", "r1", "n1", CostClass.METERED_MEDIA, 100, 1000)
    bg.settle(res.reservation_id, 100)
    try:
        bg.settle(res.reservation_id, 50)
        assert False, "二结算应拒"
    except BudgetError as e:
        print(f"[OK] double_settle_rejected → {e}")


def test_free_local_zero():
    bg = BudgetGate()
    try:
        bg.reserve("t1", "r1", "n1", CostClass.FREE_LOCAL, 0, 0)
        print("[OK] FREE_LOCAL zero allowed")
    except BudgetError as e:
        print(f"[WARN] FREE_LOCAL zero rejected → {e}")


if __name__ == "__main__":
    test_reserve_and_settle()
    test_cap_exceeded()
    test_release_on_failure()
    test_double_settle_rejected()
    test_free_local_zero()
    print("\n=== ALL BUDGET TESTS PASSED ===")
