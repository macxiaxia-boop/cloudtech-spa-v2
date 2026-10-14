"""Regression tests for atomic local completion outbox persistence."""
import sqlite3
from pathlib import Path

from workflows.v4.sqlite_run_store import SQLiteRunStore


def test_outbox_schema_and_claim_empty(tmp_path: Path):
    from workflows.v4.local_outbox import LocalCompletionOutbox
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    with sqlite3.connect(store.path) as db:
        assert db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='v4_local_outbox'"
        ).fetchone() is not None
    assert LocalCompletionOutbox(store).claim() is None


def test_outbox_event_lease_fencing(tmp_path: Path):
    from workflows.v4.local_outbox import LocalCompletionOutbox
    from workflows.v4.sqlite_run_store import RunStoreConflict
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    with store._connect() as db:
        db.execute("PRAGMA foreign_keys=OFF")
        db.execute("""INSERT INTO v4_local_outbox
          (run_id,tenant_id,event_type,payload_json)
          VALUES ('run-1','tenant-1','LOCAL_RUN_COMPLETED','{}')""")
    outbox = LocalCompletionOutbox(store)
    lease = outbox.claim()
    assert lease is not None
    assert lease.run_id == "run-1"
    assert outbox.claim() is None
    outbox.acknowledge(lease)
    assert outbox.status("run-1", "tenant-1")["state"] == "ACKED"
    import pytest
    with pytest.raises(RunStoreConflict):
        outbox.acknowledge(lease)


def test_outbox_release_and_reclaim(tmp_path: Path):
    from workflows.v4.local_outbox import LocalCompletionOutbox
    from workflows.v4.sqlite_run_store import RunStoreConflict
    import pytest
    store = SQLiteRunStore(tmp_path / "runs.sqlite3")
    with store._connect() as db:
        db.execute("PRAGMA foreign_keys=OFF")
        db.execute("""INSERT INTO v4_local_outbox
          (run_id,tenant_id,event_type,payload_json)
          VALUES ('run-2','tenant-1','LOCAL_RUN_COMPLETED','{}')""")
    outbox = LocalCompletionOutbox(store)
    first = outbox.claim()
    assert first is not None
    outbox.release(first)
    second = outbox.claim()
    assert second is not None and second.token != first.token
    assert second.attempt == 2
    with pytest.raises(RunStoreConflict):
        outbox.acknowledge(first)
    outbox.acknowledge(second)
    assert outbox.status("run-2", "tenant-1")["state"] == "ACKED"
