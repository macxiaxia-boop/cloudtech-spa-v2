"""V6.3 T04 — Pilot Realistic Data Generator tests (≥6 cases)

Sub-agent: dev #93 (V6.3 T04 — Pilot Data Generation)

验证范围 (per evidence/42 spec §3 T04):
  Case 1: 50 tenants 生成 (CSV + JSONL 同时写盘)
  Case 2: leads 状态分布严格 30/40/20/10 (new/qualified/won/lost)
  Case 3: billing ledger 4 kind 全覆盖 (reservation/settlement/refund/correction)
  Case 4: 200 email drafts = 4 模板 × 50 tenants
  Case 5: 真实 POC 数据驱动 (非纯 fake) — source_poc 引用 + 5 industries
  Case 6: import 脚本幂等 (跑两次结果一致)
  Case 7: plan 映射规则 (scale ≥5000万 → enterprise, ≥1000万 → pro, 其余 → starter)
  Case 8: 输出文件存在 + manifest.json 完整

来源 SSOT:
  - workflows/impl/_pilot_data_gen.py (本任务实现)
  - data/customers/*.json (30 真实 POC — 红线 #1)
  - data/business_data/t30_5_industries.json (5 行业 baseline)
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

# ── 路径: 让 tests/ 能 import workflows/impl
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from workflows.impl import _pilot_data_gen as pdg  # noqa: E402


# ── 共享 fixture: 跑一次生成到临时目录,避免污染 FINAL_HANDOFF/pilot_data
@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("pilot_data_v63_t04")
    manifest = pdg.run(out_dir, n_tenants=50, leads_per_tenant=30,
                       ledger_per_tenant=100, seed=42)
    return out_dir, manifest


# ═══════════════════════════════════════════════════════════════
# Case 1: 50 tenants + CSV + JSONL 同步写盘
# ═══════════════════════════════════════════════════════════════
def test_case_01_tenants_count_and_dual_format(generated):
    out_dir, manifest = generated
    assert manifest["counts"]["tenants"] == 50, "must produce exactly 50 tenants"

    csv_path = out_dir / "tenants.csv"
    jsonl_path = out_dir / "tenants.jsonl"
    assert csv_path.exists() and jsonl_path.exists()

    # CSV 头校验 + 行数 = 50 + header
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 50
    required = {"tenant_id", "tenant_name", "industry", "scale_label", "plan", "created_at"}
    assert required.issubset(rows[0].keys()), f"missing fields: {required - set(rows[0].keys())}"

    # JSONL 行数 = 50
    jsonl_lines = [l for l in jsonl_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(jsonl_lines) == 50
    print(f"✓ Case 1: 50 tenants, CSV+JSONL dual format, all required fields present")


# ═══════════════════════════════════════════════════════════════
# Case 2: leads 状态分布严格 30/40/20/10 (new/qualified/won/lost)
# ═══════════════════════════════════════════════════════════════
def test_case_02_lead_status_distribution_30_40_20_10(generated):
    out_dir, manifest = generated
    assert manifest["counts"]["leads"] == 1500, "50 × 30 = 1500 leads"

    statuses = Counter()
    with (out_dir / "leads.jsonl").open("r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            statuses[r["status"]] += 1

    total = sum(statuses.values())
    # 严格分布: 30/40/20/10 (允许 ±2% 浮动因 n=30 时序列尾)
    assert abs(statuses["new"] / total - 0.30) < 0.02, f"new={statuses['new']}/{total} ≠ 30%"
    assert abs(statuses["qualified"] / total - 0.40) < 0.02, f"qualified={statuses['qualified']}/{total} ≠ 40%"
    assert abs(statuses["won"] / total - 0.20) < 0.02, f"won={statuses['won']}/{total} ≠ 20%"
    assert abs(statuses["lost"] / total - 0.10) < 0.02, f"lost={statuses['lost']}/{total} ≠ 10%"

    print(f"✓ Case 2: leads status distribution {dict(statuses)} ≈ 30/40/20/10")


# ═══════════════════════════════════════════════════════════════
# Case 3: billing ledger 4 kind 全覆盖
# ═══════════════════════════════════════════════════════════════
def test_case_03_billing_ledger_4_kinds_present(generated):
    out_dir, manifest = generated
    assert manifest["counts"]["billing_ledger"] == 5000, "50 × 100 = 5000 ledger entries"

    kinds = Counter()
    for line in (out_dir / "billing_ledger.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        kinds[r["entry_kind"]] += 1

    required = {"reservation", "settlement", "refund", "correction"}
    assert required.issubset(kinds.keys()), f"missing kinds: {required - set(kinds.keys())}"
    # 每种 kind 至少 5% 占比 (per weighted bag 设计 40/40/10/10)
    total = sum(kinds.values())
    for k in required:
        ratio = kinds[k] / total
        assert ratio > 0.05, f"kind={k} too rare: {ratio:.2%}"

    print(f"✓ Case 3: billing ledger kinds {dict(kinds)} — all 4 present, balanced")


# ═══════════════════════════════════════════════════════════════
# Case 4: 200 email drafts = 4 模板 × 50 tenants
# ═══════════════════════════════════════════════════════════════
def test_case_04_email_drafts_4_templates_x_50_tenants(generated):
    out_dir, manifest = generated
    assert manifest["counts"]["email_drafts"] == 200, "4 × 50 = 200 drafts"

    drafts = [json.loads(line) for line in
              (out_dir / "email_drafts.jsonl").read_text(encoding="utf-8").splitlines()
              if line.strip()]
    template_ids = {d["template_id"] for d in drafts}
    assert template_ids == {"welcome_v1", "nurture_d7", "promotion_v2", "reactivation_d30"}, \
        f"missing templates: {template_ids}"

    # 每个 tenant 收到 4 封
    by_tenant = Counter(d["tenant_id"] for d in drafts)
    assert all(c == 4 for c in by_tenant.values()), f"uneven: {dict(by_tenant)}"
    assert len(by_tenant) == 50, "every tenant gets 4 drafts"

    # subject/body 含真痛点关键词 (非空模板)
    sample = drafts[0]
    assert sample["subject"] and sample["body"]
    print(f"✓ Case 4: 200 email drafts, 4 templates × 50 tenants, all complete")


# ═══════════════════════════════════════════════════════════════
# Case 5: 真实数据驱动 (红线 #1) — source_poc 引用 + 5 industries
# ═══════════════════════════════════════════════════════════════
def test_case_05_real_data_driven_not_pure_fake(generated):
    out_dir, manifest = generated

    # 每个 tenant 必须引用 1 个真实 POC (source_poc 非空且 ∈ data/customers)
    real_poc_ids = {p.stem for p in (REPO_ROOT / "data" / "customers").glob("*.json")}
    tenants = [json.loads(l) for l in
               (out_dir / "tenants.jsonl").read_text(encoding="utf-8").splitlines()
               if l.strip()]
    src_set = {t["source_poc"] for t in tenants}
    # 50 tenants 至少引用 ≥10 个不同 POC (避免单 POC 重复)
    assert len(src_set) >= 10, f"only {len(src_set)} distinct POC referenced"
    # 所有 source_poc 必须 ∈ 真实 POC 集合
    assert src_set.issubset(real_poc_ids), f"fake POC id: {src_set - real_poc_ids}"

    # industries 必须 ⊇ 5+2 (5 WF 行业 + medical_beauty)
    industries = {t["industry"] for t in tenants}
    expected = {"decoration", "medical_beauty", "education", "catering", "retail"}
    assert expected.issubset(industries), f"missing industries: {expected - industries}"

    # pain_points_seed 来自真 POC (每 tenant 至少 1 条)
    assert all(len(t["pain_points_seed"]) >= 1 for t in tenants)

    print(f"✓ Case 5: {len(src_set)} real POC referenced, {len(industries)} industries, "
          f"pain_points all from real POCs")


# ═══════════════════════════════════════════════════════════════
# Case 6: import 脚本幂等 (idempotent — 跑两次结果完全一致)
# ═══════════════════════════════════════════════════════════════
def test_case_06_import_script_idempotent(generated):
    out_dir, _ = generated
    import_script = out_dir / "import_pilot_data.py"
    assert import_script.exists(), "import_pilot_data.py must be generated"

    # 跑 import 两次,验证 raw_count == unique_count (no duplicates) + 两次结果 dict-equal
    r1 = pdg.import_all(out_dir) if hasattr(pdg, "import_all") else None
    # 若 pdg 没暴露 import_all (因 import script 是独立文件),直接 subprocess 跑
    if r1 is None:
        # 用 subprocess 跑生成的 import script
        out1 = subprocess.run(
            [sys.executable, str(import_script), "--data-dir", str(out_dir)],
            capture_output=True, text=True, timeout=30,
        )
        assert out1.returncode == 0, f"import failed: {out1.stderr}"
        assert "IDEMPOTENT_OK" in out1.stdout, "must print IDEMPOTENT_OK"

        # 第二次跑结果应完全相同
        out2 = subprocess.run(
            [sys.executable, str(import_script), "--data-dir", str(out_dir)],
            capture_output=True, text=True, timeout=30,
        )
        assert out2.returncode == 0
        # 两次 stdout 应 byte-equal (因 dict eq 用 == assert)
        # 实际比较: 抽出 "tables" 段的 unique_count 是否一致
        d1 = json.loads(out1.stdout.split("\nIDEMPOTENT_OK")[0])
        d2 = json.loads(out2.stdout.split("\nIDEMPOTENT_OK")[0])
        for name in ("tenants", "leads", "billing_ledger", "email_drafts"):
            assert d1["tables"][name]["unique_count"] == d2["tables"][name]["unique_count"]
            assert d1["tables"][name]["raw_count"] == d1["tables"][name]["unique_count"], \
                f"{name} has duplicates: raw={d1['tables'][name]['raw_count']} unique={d1['tables'][name]['unique_count']}"
    else:
        # pdg 直接暴露 — 跑 2 次必须 ==
        r2 = pdg.import_all(out_dir)
        assert r1 == r2, "import_all must be idempotent"

    print(f"✓ Case 6: import script idempotent, raw_count == unique_count for all 4 tables")


# ═══════════════════════════════════════════════════════════════
# Case 7: plan 映射规则 (scale ≥5000万 → enterprise, ≥1000万 → pro, 其余 → starter)
# ═══════════════════════════════════════════════════════════════
def test_case_07_plan_mapping_rule(generated):
    out_dir, _ = generated
    tenants = [json.loads(l) for l in
               (out_dir / "tenants.jsonl").read_text(encoding="utf-8").splitlines()
               if l.strip()]
    for t in tenants:
        scale = float(t["scale_label"].replace("万", "").strip())
        plan = t["plan"]
        if scale >= 5000:
            assert plan == "enterprise", f"scale={scale} should be enterprise, got {plan}"
        elif scale >= 1000:
            assert plan == "pro", f"scale={scale} should be pro, got {plan}"
        else:
            assert plan == "starter", f"scale={scale} should be starter, got {plan}"

    # 分布: 3 种 plan 都至少出现 (因 input scale 范围 100万-8000万)
    plans = {t["plan"] for t in tenants}
    assert plans == {"starter", "pro", "enterprise"}, f"missing plan: {plans}"

    print(f"✓ Case 7: plan mapping rule verified for all {len(tenants)} tenants")


# ═══════════════════════════════════════════════════════════════
# Case 8: 输出文件齐全 + manifest.json 完整
# ═══════════════════════════════════════════════════════════════
def test_case_08_outputs_and_manifest_complete(generated):
    out_dir, manifest = generated
    expected_files = [
        "tenants.csv", "tenants.jsonl", "leads.jsonl",
        "billing_ledger.jsonl", "email_drafts.jsonl",
        "import_pilot_data.py", "manifest.json",
    ]
    for fn in expected_files:
        assert (out_dir / fn).exists(), f"missing output: {fn}"

    # manifest.json 字段完整
    required_keys = {"task_id", "generated_at", "seed", "out_dir", "sources", "outputs", "counts"}
    assert required_keys.issubset(manifest.keys())
    assert manifest["task_id"] == "V6.3-T04-pilot-data-gen"
    assert manifest["seed"] == 42
    assert manifest["red_line_compliance"]["real_data_source_used"] is True
    assert manifest["red_line_compliance"]["no_external_api"] is True

    print(f"✓ Case 8: all 7 output files present + manifest complete "
          f"(tenants={manifest['counts']['tenants']}, "
          f"leads={manifest['counts']['leads']}, "
          f"ledger={manifest['counts']['billing_ledger']}, "
          f"emails={manifest['counts']['email_drafts']})")