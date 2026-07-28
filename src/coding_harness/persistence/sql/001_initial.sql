CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE audit_events (
    audit_order INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    event_kind TEXT NOT NULL,
    subject_identity TEXT NOT NULL,
    occurred_at INTEGER NOT NULL,
    source_state TEXT,
    target_state TEXT,
    transition_trigger TEXT,
    transition_reason TEXT,
    permitted INTEGER CHECK (permitted IS NULL OR permitted IN (0, 1))
);

CREATE TRIGGER audit_events_no_update
BEFORE UPDATE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit events are append-only');
END;

CREATE TRIGGER audit_events_no_delete
BEFORE DELETE ON audit_events
BEGIN
    SELECT RAISE(ABORT, 'audit events are append-only');
END;

CREATE TABLE plan_versions (
    identity TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    sequence INTEGER NOT NULL,
    content_digest TEXT NOT NULL,
    display_text TEXT NOT NULL,
    UNIQUE (task_id, sequence)
);

CREATE TABLE contract_versions (
    identity TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    sequence INTEGER NOT NULL,
    content_digest TEXT NOT NULL,
    display_text TEXT NOT NULL,
    UNIQUE (task_id, sequence)
);

CREATE TABLE budget_versions (
    identity TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    sequence INTEGER NOT NULL,
    payload TEXT NOT NULL,
    UNIQUE (task_id, sequence)
);

CREATE TABLE approvals (
    approval_identity TEXT NOT NULL,
    revision INTEGER NOT NULL,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    idempotency_key TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (approval_identity, revision)
);

CREATE INDEX approvals_by_idempotency
ON approvals(task_id, idempotency_key, revision);

CREATE TABLE changeset_confirmations (
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    idempotency_key TEXT NOT NULL,
    changeset_digest TEXT NOT NULL,
    baseline_manifest_digest TEXT NOT NULL,
    plan_version_identity TEXT NOT NULL,
    acceptance_contract_version_identity TEXT NOT NULL,
    expected_state TEXT NOT NULL,
    occurred_at INTEGER NOT NULL,
    PRIMARY KEY (task_id, idempotency_key)
);

CREATE TABLE apply_observations (
    transaction_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    decision TEXT NOT NULL,
    phase TEXT,
    observed_task_state TEXT NOT NULL,
    recovery_state TEXT,
    plan_digest TEXT,
    baseline_digest TEXT,
    changeset_digest TEXT,
    journal_reference TEXT,
    index_digest_after TEXT,
    reason TEXT NOT NULL,
    occurred_at INTEGER NOT NULL
);
