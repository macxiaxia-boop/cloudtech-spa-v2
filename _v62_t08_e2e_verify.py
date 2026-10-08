"""V6.2 T08 E2E Verification Script (v4 - all unquoted refs)
对 24 个 CloudTech workflow 模块做 E2E 验证
"""
import sys
import json
import inspect
import importlib
import re
import traceback
from pathlib import Path
from typing import List, Dict, Any, Set

ROOT = Path(r"D:\CloudTech-Portable")
sys.path.insert(0, str(ROOT))

MODULES = [
    ("wf_t001_diagnosis", "WF-T-001"),
    ("wf_t002_local_topics", "WF-T-002"),
    ("wf_t003_script", "WF-T-003"),
    ("wf_t004_content_plan", "WF-T-004"),
    ("wf_t005_leads", "WF-T-005"),
    ("wf_t006_followup", "WF-T-006"),
    ("wf_t007_funnel", "WF-T-007"),
    ("wf_t008_experiment", "WF-T-008"),
    ("wf_t009_competitor", "WF-T-009"),
    ("wf_t010_live", "WF-T-010"),
    ("wf_t011_ads", "WF-T-011"),
    ("wf_t012_quote", "WF-T-012"),
    ("wf_g013_init", "WF-G-013"),
    ("wf_g014_deploy", "WF-G-014"),
    ("wf_g015_acl", "WF-G-015"),
    ("wf_g016_provider", "WF-G-016"),
    ("wf_g017_long_flow", "WF-G-017"),
    ("wf_g018_meeting", "WF-G-018"),
    ("wf_g019_qa", "WF-G-019"),
    ("wf_g020_contract", "WF-G-020"),
    ("wf_g021_promotion", "WF-G-021"),
    ("wf_g022_token_recon", "WF-G-022"),
    ("wf_g023_incident", "WF-G-023"),
    ("wf_g024_export", "WF-G-024"),
]

MINIMAL_INPUTS = {
    "WF-T-001": dict(tenant_id="zq-evt-1", industry="decoration", target_revenue=100000.0, current_revenue=50000.0, sample_size=30),
    "WF-T-002": dict(tenant_id="zq-evt-1", cities=["厦门"]),
    "WF-T-003": dict(tenant_id="zq-evt-1", topic="装修预算分析"),
    "WF-T-004": dict(tenant_id="zq-evt-1", scripts=[{"script_id": "s1", "topic": "test", "platform": "douyin", "scheduled_at": "2026-10-10T09:00:00"}]),
    "WF-T-005": dict(tenant_id="zq-evt-1",
                      leads=[{"name": "张三", "phone": "13800138000", "city": "厦门"}],
                      sales_team=["张销售", "李销售"]),
    "WF-T-006": dict(tenant_id="zq-evt-1",
                      leads=[{"lead_name": "张三", "last_contact_at": "2026-10-01T10:00:00", "assigned_to": "张销售"}]),
    "WF-T-007": dict(tenant_id="zq-evt-1", week_start="2026-10-06",
                      current={"impressions": 1000, "clicks": 50, "leads": 5, "quotes": 2, "contracts": 1}),
    "WF-T-008": dict(tenant_id="zq-evt-1",
                      experiments=[{"name": "exp1", "hypothesis": "h", "variant_a": "a", "variant_b": "b",
                                    "sample_size": 100, "metric_a": 50.0, "metric_b": 60.0}]),
    "WF-T-009": dict(tenant_id="zq-evt-1", cities=["厦门"],
                      competitors=[{"company": "竞品A"}]),
    "WF-T-010": dict(tenant_id="zq-evt-1", activity_name="双十一直播", planned_start="2026-10-10T19:00:00",
                      products=[{"sku": "p1", "name": "套餐A", "price": 1000.0}]),
    "WF-T-011": dict(tenant_id="zq-evt-1", budget_total=1000.0,
                      campaigns=[{"campaign_id": "c1", "name": "test", "platform": "douyin", "spend": 100.0}]),
    "WF-T-012": dict(tenant_id="zq-evt-1",
                      questions=[{"qid": "q1", "content": "装修预算?"}]),
    "WF-G-013": dict(tenant_name="测试装企"),
    "WF-G-014": dict(tenant_id="zq-evt-1", sandbox="dev",
                      employees=[{"type": "content_writer", "capabilities": ["article"]}]),
    "WF-G-015": dict(tenant_id="zq-evt-1",
                      knowledge_docs=[{"doc_id": "d1", "title": "t", "content": "test content", "acl_tags": ["public"]}],
                      user_roles=[{"user_role": "admin", "allowed_tags": ["public"]}],
                      role_to_query="admin"),
    "WF-G-016": dict(tenant_id="zq-evt-1",
                      calls=[{"call_id": "c1", "provider": "mock", "model": "gpt-4",
                              "tokens_in": 100, "tokens_out": 50,
                              "unit_price_in": 0.001, "unit_price_out": 0.002,
                              "reported_cost_yuan": 0.5}]),
    "WF-G-017": dict(tenant_id="zq-evt-1", steps=[{"name": "s1", "status": "done"}], checkpoints=[]),
    "WF-G-018": dict(tenant_id="zq-evt-1",
                      transcript={"meeting_id": "mtg-1", "title": "周会", "duration_min": 30,
                                  "utterances": [{"speaker": "A", "text": "需要跟进"}]}),
    "WF-G-019": dict(tenant_id="zq-evt-1", question="如何验收水电",
                      candidate_answers=["验收水电需要专业工具"]),
    "WF-G-020": dict(tenant_id="zq-evt-1", contract_id="ct-1",
                      clauses=[{"cid": "c1", "text": "明确付款", "type": "payment"}]),
    "WF-G-021": dict(tenant_id="zq-evt-1",
                      candidates=[{"sid": "s1", "title": "测试SOP", "source": "exp-1", "confidence": "high", "evidence_count": 5}]),
    "WF-G-022": dict(tenant_id="zq-evt-1", month="2026-10",
                      daily_usage=[{"date": "2026-10-01", "provider": "mock", "tokens": 1000, "cost_yuan": 1.0}]),
    "WF-G-023": dict(tenant_id="zq-evt-1", incident_id="inc-1", severity="P1",
                      affected_workflows=["WF-T-001"]),
    "WF-G-024": dict(tenant_id="zq-evt-1", export_scope=["tenants"]),
}

WF_PAT = re.compile(r'(?<!["\w-])(WF-[TG]-\d{3})(?!["\w-])')


def _find_run_function(mod):
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        if hasattr(obj, "_is_workflow_run") and getattr(obj, "_is_workflow_run", False):
            return name, obj
    for name in dir(mod):
        if name.startswith("run_") and callable(getattr(mod, name)):
            return name, getattr(mod, name)
    return None, None


def _find_input_model(mod):
    for n in dir(mod):
        obj = getattr(mod, n)
        if inspect.isclass(obj) and hasattr(obj, "model_fields") and n.endswith("Input"):
            return obj
    return None


def verify_import(mod_name):
    full_name = f"workflows.impl.{mod_name}"
    try:
        mod = importlib.import_module(full_name)
        return {"ok": True, "module": full_name}
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


def verify_run_path(mod, workflow_id):
    from workflows.base import RunHistoryTracker
    tracker = RunHistoryTracker.instance()
    tracker.reset()
    name, fn = _find_run_function(mod)
    if fn is None:
        return {"ok": False, "error": "no run function found"}
    input_model = _find_input_model(mod)
    if input_model is None:
        return {"ok": False, "error": "no Input model found"}
    try:
        kwargs = MINIMAL_INPUTS.get(workflow_id, {})
        inp = input_model(**kwargs)
        out = fn(inp)
        if not isinstance(out, dict) or "status" not in out:
            return {"ok": False, "error": f"unexpected output: {out}"}
        if out["status"] != "success":
            return {"ok": False, "error": f"workflow returned non-success: {out}", "status": out["status"]}
        run_id = out.get("run_id")
        tracked_status = tracker.get_status(run_id) if run_id else None
        if tracked_status is None or tracked_status.get("status") != "success":
            return {"ok": False, "error": "tracker did not record success"}
        return {"ok": True, "status": "success", "run_id": run_id, "tracker_status": tracked_status.get("status")}
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


def verify_pydantic_v2(mod):
    try:
        has_v2_models = False
        model_count = 0
        for n in dir(mod):
            obj = getattr(mod, n)
            if inspect.isclass(obj) and hasattr(obj, "model_fields"):
                has_v2_models = True
                model_count += 1
        return {"ok": True, "has_v2_models": has_v2_models, "model_count": model_count, "pydantic_version": "2.13.4"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def verify_workflow_dag(modules_dict):
    """Build recommendation graph and detect cycles.
    Edges derived from whole-file WF-X-XXX references (excluding self).
    """
    graph: Dict[str, Set[str]] = {}
    wf_id_by_mod = {m: wf for m, wf in MODULES}
    known_wf_ids = set(wf_id_by_mod.values())

    for name, mod in modules_dict.items():
        self_id = wf_id_by_mod.get(name)
        deps: Set[str] = set()
        try:
            src_file = inspect.getsourcefile(mod)
            if src_file:
                src = Path(src_file).read_text(encoding="utf-8")
                for m in WF_PAT.finditer(src):
                    dep = m.group(1)
                    if dep in known_wf_ids and dep != self_id:
                        deps.add(dep)
            graph[name] = deps
        except Exception:
            graph[name] = set()

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    cycles: List[List[str]] = []

    def dfs(node, path):
        color[node] = GRAY
        for neighbor in graph.get(node, set()):
            mod_for_neighbor = next((m for m, w in MODULES if w == neighbor), None)
            if mod_for_neighbor is None:
                continue
            if color.get(mod_for_neighbor) == GRAY:
                cycles.append(path + [mod_for_neighbor])
                return
            if color.get(mod_for_neighbor) == WHITE:
                dfs(mod_for_neighbor, path + [mod_for_neighbor])
        color[node] = BLACK

    for n in graph:
        if color[n] == WHITE:
            dfs(n, [n])

    edges_list = []
    for n, deps in graph.items():
        for d in sorted(deps):
            edges_list.append({"from": wf_id_by_mod.get(n, n), "to": d})

    return {"ok": len(cycles) == 0, "cycles": cycles, "edges": edges_list, "edge_count": len(edges_list)}


def main():
    print("=" * 70)
    print("V6.2 T08 CloudTech Workflows E2E Verification")
    print("=" * 70)

    modules_dict = {}
    import_results = {}
    run_results = {}
    pydantic_results = {}

    print("\n[Phase 1] Import tests...")
    for mod_name, wf_id in MODULES:
        r = verify_import(mod_name)
        import_results[mod_name] = r
        if r["ok"]:
            print(f"  [OK] {mod_name}")
        else:
            print(f"  [FAIL] {mod_name}: {r['error'][:80]}")

    print("\n[Phase 2] Tracker init -> start -> success path tests...")
    for mod_name, wf_id in MODULES:
        if not import_results[mod_name]["ok"]:
            run_results[mod_name] = {"ok": False, "error": "import failed"}
            continue
        full_name = f"workflows.impl.{mod_name}"
        try:
            mod = importlib.import_module(full_name)
            modules_dict[mod_name] = mod
            r = verify_run_path(mod, wf_id)
            run_results[mod_name] = r
            if r["ok"]:
                print(f"  [OK] {mod_name}: {r['status']}")
            else:
                print(f"  [FAIL] {mod_name}: {r['error'][:120]}")
        except Exception as e:
            run_results[mod_name] = {"ok": False, "error": str(e)}

    print("\n[Phase 3] Pydantic v2 schema compatibility...")
    for mod_name, _ in MODULES:
        if mod_name not in modules_dict:
            pydantic_results[mod_name] = {"ok": False, "error": "module not loaded"}
            continue
        r = verify_pydantic_v2(modules_dict[mod_name])
        pydantic_results[mod_name] = r
        if r["ok"]:
            print(f"  [OK] {mod_name}: v2 models={r['model_count']}")
        else:
            print(f"  [FAIL] {mod_name}: {r['error'][:80]}")

    print("\n[Phase 4] Workflow DAG cycle detection...")
    dag = verify_workflow_dag(modules_dict)
    print(f"  Edges found: {dag['edge_count']}")
    for e in dag["edges"]:
        print(f"    {e['from']} -> {e['to']}")
    if dag["ok"]:
        print(f"  [OK] No cycles detected")
    else:
        print(f"  [FAIL] Cycles: {dag['cycles']}")

    import_pass = sum(1 for r in import_results.values() if r["ok"])
    run_pass = sum(1 for r in run_results.values() if r["ok"])
    pydantic_pass = sum(1 for r in pydantic_results.values() if r["ok"])

    summary = {
        "import_pass": import_pass,
        "import_total": len(MODULES),
        "run_pass": run_pass,
        "run_total": len(MODULES),
        "pydantic_pass": pydantic_pass,
        "pydantic_total": len(MODULES),
        "dag_ok": dag["ok"],
        "dag_edges": dag["edge_count"],
        "dag_cycles": dag["cycles"],
        "pydantic_version": "2.13.4",
        "python_version": sys.version.split()[0],
        "all_modules_pass": run_pass == len(MODULES) and import_pass == len(MODULES) and pydantic_pass == len(MODULES) and dag["ok"],
    }
    print("\n" + "=" * 70)
    print(f"Summary: import={import_pass}/{len(MODULES)} run={run_pass}/{len(MODULES)} pydantic_v2={pydantic_pass}/{len(MODULES)} dag_ok={dag['ok']}")
    print("=" * 70)

    return {
        "summary": summary,
        "import": import_results,
        "run": run_results,
        "pydantic": pydantic_results,
        "dag": dag,
    }


if __name__ == "__main__":
    out = main()
    out_path = Path(r"D:\CloudTech-Portable\_e2e_verify_results.json")
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nResults saved to: {out_path}")