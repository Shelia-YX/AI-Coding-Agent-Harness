CREATE TABLE domain_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_kind TEXT NOT NULL,
    occurred_at INTEGER NOT NULL CHECK (occurred_at >= 0),
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    entity_identity TEXT NOT NULL,
    entity_revision INTEGER CHECK (
        entity_revision IS NULL OR entity_revision >= 1
    ),
    payload TEXT NOT NULL,
    evidence_refs TEXT NOT NULL
);

CREATE INDEX domain_events_by_task
ON domain_events(task_id, event_id);

CREATE TRIGGER domain_events_no_update
BEFORE UPDATE ON domain_events
BEGIN
    SELECT RAISE(ABORT, 'domain events are append-only');
END;

CREATE TRIGGER domain_events_no_delete
BEFORE DELETE ON domain_events
BEGIN
    SELECT RAISE(ABORT, 'domain events are append-only');
END;
