"""Bounded in-memory storage for active and recent extraction runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.schemas import (
    Issue,
    RunMetadata,
    RunProgress,
    RunResult,
    RunState,
    RunStatus,
)


@dataclass
class RunRecord:
    state: RunState
    filename: str


class RunStore:
    """Keep run state in process memory with expiry and a storage bound."""

    def __init__(self, *, ttl_minutes: int, max_stored_runs: int, max_active_runs: int) -> None:
        self._ttl = timedelta(minutes=ttl_minutes)
        self._max_stored_runs = max_stored_runs
        self._max_active_runs = max_active_runs
        self._runs: dict[str, RunRecord] = {}

    @property
    def active_limit(self) -> int:
        return min(self._max_active_runs, self._max_stored_runs)

    def create(self, state: RunState, filename: str) -> bool:
        self._prune()
        if self.active_count() >= self.active_limit:
            return False
        self._runs[state.run_id] = RunRecord(state=state, filename=filename)
        self._enforce_storage_limit()
        return True

    def get(self, run_id: str) -> RunRecord | None:
        self._prune()
        return self._runs.get(run_id)

    def active_count(self) -> int:
        return sum(
            record.state.status in {RunStatus.queued, RunStatus.running}
            for record in self._runs.values()
        )

    def update_progress(self, run_id: str, progress: RunProgress) -> None:
        record = self._runs.get(run_id)
        if record is not None:
            record.state = record.state.model_copy(update={"progress": progress})

    def finish(
        self,
        run_id: str,
        *,
        status: RunStatus,
        progress: RunProgress,
        result: RunResult | None,
        metadata: RunMetadata,
        errors: list[Issue],
        warnings: list[Issue],
        finished_at: datetime | None = None,
    ) -> None:
        record = self._runs.get(run_id)
        if record is None:
            return
        record.state = record.state.model_copy(
            update={
                "status": status,
                "finished_at": finished_at or datetime.now(UTC),
                "progress": progress,
                "result": result,
                "metadata": metadata,
                "errors": errors,
                "warnings": warnings,
            }
        )
        self._enforce_storage_limit()

    def _prune(self) -> None:
        now = datetime.now(UTC)
        expired = [
            run_id
            for run_id, record in self._runs.items()
            if record.state.status not in {RunStatus.queued, RunStatus.running}
            and record.state.finished_at is not None
            and now - record.state.finished_at > self._ttl
        ]
        for run_id in expired:
            del self._runs[run_id]

    def _enforce_storage_limit(self) -> None:
        while len(self._runs) > self._max_stored_runs:
            terminal_runs = [
                (record.state.created_at, run_id)
                for run_id, record in self._runs.items()
                if record.state.status not in {RunStatus.queued, RunStatus.running}
            ]
            if not terminal_runs:
                return
            _, oldest_run_id = min(terminal_runs)
            del self._runs[oldest_run_id]
