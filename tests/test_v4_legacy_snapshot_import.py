"""PR1-to-PR2 legacy snapshot preservation; never upgrades unverified results."""
import json
import sqlite3

import pytest

from workflows.v4.legacy_snapshot_import import quarantine_legacy
from workflows.v4.sqlite_run_store import SQLiteRunStore


def legacy_db(tmp_path):
    source = tmp_path / "legacy-pr1.sqlite3"
    with sqlite3.connect(source) as db:
        db.execute("""CREATE TABLE v4_run_snapshots (
            run_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            payload_json TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        for run_id, tenant, status in [
            ("wpr_old1", "tenant-a", "COMPLETED"),
            ("wpr_old2", "tenant-b", "RUNNING"),
        ]:
            payload = {
                "run_id": run_id, "tenant_id": tenant, "status": status,
                "nodes": [], "input_bindings": {"html": "<p>private input stays quarantined</p>"},
            }
            db.execute("INSERT INTO v4_run_snapshots VALUES(?,?,?,?)",
                       (run_id, tenant, json.dumps(payload), "2026-10-10T10:00:00"))
    return source


def target_store(tmp_path):
    path = tmp_path / "pr2.sqlite3"
    SQLiteRunStore(path)
    return path


def test_dry_run_has_zero_side_effects_and_never_emits_customer_html(tmp_path):
    source, target = legacy_db(tmp_path), target_store(tmp_path)
    report = quarantine_legacy(source, target)
    assert report == {
        "inspected": 2, "quarantined_new": 0, "idempotent_existing": 0,
        "active_runs_imported": 0, "worker_invoked": False,
        "production_ready": False, "applied": False,
    }
    assert "private input" not in json.dumps(report)
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT COUNT(*) FROM v4_runs").fetchone()[0] == 0
        assert db.execute("""SELECT name FROM sqlite_master
            WHERE name='v4_legacy_snapshot_quarantine'""").fetchone() is None


def test_apply_is_nonproduction_quarantine_only_and_idempotent(tmp_path):
    source, target = legacy_db(tmp_path), target_store(tmp_path)
    first = quarantine_legacy(source, target, apply=True, environment="test")
    assert first["quarantined_new"] == 2
    assert first["active_runs_imported"] == 0
    assert first["worker_invoked"] is False
    second = quarantine_legacy(source, target, apply=True, environment="staging")
    assert second["quarantined_new"] == 0
    assert second["idempotent_existing"] == 2
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT COUNT(*) FROM v4_runs").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM v4_node_receipts").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM v4_local_outbox").fetchone()[0] == 0
        quarantined = db.execute("""SELECT run_id,tenant_id,legacy_status,review_state,
                                          payload_json FROM v4_legacy_snapshot_quarantine
                                  ORDER BY run_id""").fetchall()
        assert len(quarantined) == 2
        assert [r[2] for r in quarantined] == ["COMPLETED", "RUNNING"]
        assert all(r[3] == "PENDING" for r in quarantined)
        assert "private input" in quarantined[0][4]


def test_production_or_unspecified_environment_may_not_apply(tmp_path, monkeypatch):
    source, target = legacy_db(tmp_path), target_store(tmp_path)
    monkeypatch.delenv("CLOUDTECH_ENV", raising=False)
    for env in ["production", "", "prod"]:
        with pytest.raises(PermissionError):
            quarantine_legacy(source, target, apply=True, environment=env)
    with sqlite3.connect(target) as db:
        assert db.execute(
            "SELECT name FROM sqlite_master WHERE name='v4_legacy_snapshot_quarantine'"
        ).fetchone() is None


@pytest.mark.parametrize("mutation", ["invalid-json", "wrong-tenant", "invalid-status"])
def test_corrupt_source_fails_preflight_without_partial_import(tmp_path, mutation):
    source, target = legacy_db(tmp_path), target_store(tmp_path)
    with sqlite3.connect(source) as db:
        if mutation == "invalid-json":
            value = "{invalid"
        else:
            value = json.loads(db.execute(
                "SELECT payload_json FROM v4_run_snapshots WHERE run_id='wpr_old2'"
            ).fetchone()[0])
            if mutation == "wrong-tenant":
                value["tenant_id"] = "other-tenant"
            else:
                value["status"] = "TRUST_ME_PRODUCTION_READY"
            value = json.dumps(value)
        db.execute("UPDATE v4_run_snapshots SET payload_json=? WHERE run_id='wpr_old2'",
                   (value,))
    with pytest.raises(ValueError):
        quarantine_legacy(source, target, apply=True, environment="test")
    with sqlite3.connect(target) as db:
        assert db.execute(
            "SELECT name FROM sqlite_master WHERE name='v4_legacy_snapshot_quarantine'"
        ).fetchone() is None


def test_source_mutation_collision_rolls_back_without_overwriting_original(tmp_path):
    source, target = legacy_db(tmp_path), target_store(tmp_path)
    assert quarantine_legacy(source, target, apply=True, environment="test")[
        "quarantined_new"] == 2
    with sqlite3.connect(source) as db:
        orig = json.loads(db.execute(
            "SELECT payload_json FROM v4_run_snapshots WHERE run_id='wpr_old1'"
        ).fetchone()[0])
        orig["input_bindings"]["html"] = "changed underlying customer input"
        db.execute("UPDATE v4_run_snapshots SET payload_json=? WHERE run_id='wpr_old1'",
                   (json.dumps(orig),))
    with pytest.raises(ValueError, match="changed"):
        quarantine_legacy(source, target, apply=True, environment="test")
    with sqlite3.connect(target) as db:
        assert db.execute(
            "SELECT COUNT(*) FROM v4_legacy_snapshot_quarantine"
        ).fetchone()[0] == 2
        saved = db.execute(
            "SELECT payload_json FROM v4_legacy_snapshot_quarantine WHERE run_id='wpr_old1'"
        ).fetchone()[0]
        assert "changed underlying customer input" not in saved


def test_conflicts_with_active_pr2_run_are_rejected(tmp_path):
    source, target = legacy_db(tmp_path), target_store(tmp_path)
    with sqlite3.connect(target) as db:
        db.execute("""INSERT INTO v4_runs(
          run_id,tenant_id,idempotency_key,fingerprint,path_id,status,
          created_at,updated_at,version,snapshot
        ) VALUES(?,?,?,?,?,?,?,?,0,?)""", (
            "wpr_old2", "tenant-b", None, "fingerprint", "WP-LOCAL-ARTICLE-EXTRACT",
            "PARTIAL", "now", "now", "{}",
        ))
    with pytest.raises(ValueError, match="collision"):
        quarantine_legacy(source, target, apply=True, environment="test")
    with sqlite3.connect(target) as db:
        # The first record might have been written before collision: BEGIN
        # IMMEDIATE must roll back all prior quarantined rows on failure.
        assert db.execute(
            "SELECT name FROM sqlite_master WHERE name='v4_legacy_snapshot_quarantine'"
        ).fetchone() is None


def test_invalid_or_missing_target_never_creates_live_store(tmp_path):
    source = legacy_db(tmp_path)
    with pytest.raises(FileNotFoundError):
        quarantine_legacy(source, tmp_path / "missing.sqlite3", apply=True, environment="test")
    target = tmp_path / "not-a-pr2.sqlite3"
    with sqlite3.connect(target) as db:
        db.execute("CREATE TABLE unrelated (id INTEGER)")
    with pytest.raises(ValueError, match="valid PR2"):
        quarantine_legacy(source, target, apply=True, environment="test")
