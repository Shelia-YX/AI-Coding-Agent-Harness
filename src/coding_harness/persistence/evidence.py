"""Evidence references and persistent domain-event reading."""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from coding_harness.domain.events import (
    DomainEvent,
    DomainEventKind,
    EvidenceKind,
    EvidenceLifecycle,
    EvidenceRef,
)


class EvidenceError(RuntimeError):
    pass


def _evidence_from_json(payload: object) -> tuple[EvidenceRef, ...]:
    if type(payload) is not str:
        raise EvidenceError("persisted event evidence is invalid")
    try:
        values = json.loads(payload)
        if type(values) is not list:
            raise ValueError
        return tuple(
            EvidenceRef(
                kind=EvidenceKind(item["kind"]),
                relative_path=item["relative_path"],
                content_digest=item["content_digest"],
                size_bytes=item["size_bytes"],
                lifecycle=EvidenceLifecycle(item["lifecycle"]),
            )
            for item in values
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise EvidenceError("persisted event evidence is invalid") from None


def _payload_from_json(payload: object) -> tuple[tuple[str, str], ...]:
    if type(payload) is not str:
        raise EvidenceError("persisted event payload is invalid")
    try:
        values = json.loads(payload)
        if type(values) is not list:
            raise ValueError
        result = tuple(
            (item[0], item[1])
            for item in values
            if type(item) is list and len(item) == 2
        )
        if len(result) != len(values):
            raise ValueError
        return result
    except (TypeError, ValueError, json.JSONDecodeError):
        raise EvidenceError("persisted event payload is invalid") from None


class EventReader:
    def __init__(self, *, database_path: Path) -> None:
        if not isinstance(database_path, Path):
            raise ValueError("event reader is invalid")
        self._database_path = database_path

    def after(
        self,
        *,
        event_id: int,
        limit: int,
    ) -> tuple[DomainEvent, ...]:
        if (
            type(event_id) is not int
            or event_id < 0
            or type(limit) is not int
            or limit < 1
            or limit > 1000
        ):
            raise ValueError("event reader cursor or limit is invalid")
        try:
            database_uri = self._database_path.absolute().as_uri() + "?mode=ro"
            connection = sqlite3.connect(database_uri, timeout=5, uri=True)
            connection.execute("PRAGMA query_only = ON")
        except sqlite3.Error:
            raise EvidenceError("event persistence is unavailable") from None
        try:
            rows = connection.execute(
                "SELECT event_id, event_kind, occurred_at, task_id, "
                "entity_identity, entity_revision, payload, evidence_refs "
                "FROM domain_events WHERE event_id > ? "
                "ORDER BY event_id ASC LIMIT ?",
                (event_id, limit),
            ).fetchall()
        except sqlite3.Error:
            raise EvidenceError("event persistence query failed") from None
        finally:
            connection.close()
        try:
            return tuple(
                DomainEvent(
                    event_id=row[0],
                    event_kind=DomainEventKind(row[1]),
                    occurred_at=row[2],
                    task_id=row[3],
                    entity_identity=row[4],
                    entity_revision=row[5],
                    payload=_payload_from_json(row[6]),
                    evidence_refs=_evidence_from_json(row[7]),
                )
                for row in rows
            )
        except (TypeError, ValueError):
            raise EvidenceError("persisted domain event is invalid") from None


__all__ = [
    "EvidenceError",
    "EvidenceKind",
    "EvidenceLifecycle",
    "EvidenceRef",
    "EventReader",
]
