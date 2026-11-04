from datetime import UTC, datetime, timedelta

from app.api.run_store import RunStore
from app.core.schemas import RunProgress, RunState, RunStatus


def _state(
    run_id: str,
    *,
    status: RunStatus = RunStatus.queued,
    created_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> RunState:
    return RunState(
        run_id=run_id,
        status=status,
        created_at=created_at or datetime.now(UTC),
        finished_at=finished_at,
        progress=RunProgress(
            stage="loading",
            pages_total=0,
            pages_done=0,
            pages_failed=0,
            pages=[],
        ),
        result=None,
        metadata=None,
        errors=[],
        warnings=[],
    )


def test_run_store_limits_active_runs_and_evicts_oldest_terminal() -> None:
    active_store = RunStore(ttl_minutes=60, max_stored_runs=1, max_active_runs=4)
    assert active_store.create(_state("active"), "active.pdf")
    assert active_store.active_limit == 1
    assert not active_store.create(_state("over-limit"), "second.pdf")

    bounded_store = RunStore(ttl_minutes=60, max_stored_runs=1, max_active_runs=4)
    terminal = _state(
        "first",
        status=RunStatus.failed,
        finished_at=datetime.now(UTC),
    )
    assert bounded_store.create(terminal, "first.pdf")
    assert bounded_store.create(_state("second"), "second.pdf")
    assert bounded_store.get("first") is None
    assert bounded_store.get("second") is not None


def test_run_store_expires_terminal_results_after_ttl() -> None:
    store = RunStore(ttl_minutes=1, max_stored_runs=10, max_active_runs=2)
    state = _state(
        "expired",
        status=RunStatus.failed,
        finished_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    assert store.create(state, "expired.pdf")
    assert store.get("expired") is None
