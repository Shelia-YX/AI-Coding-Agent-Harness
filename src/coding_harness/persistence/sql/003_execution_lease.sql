CREATE TABLE execution_leases (
    lease_id TEXT PRIMARY KEY,
    slot_identity TEXT NOT NULL CHECK (
        slot_identity = 'execution:global'
    ),
    task_id TEXT NOT NULL REFERENCES tasks(task_id),
    run_id TEXT NOT NULL,
    owner_identity TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK (purpose IN ('EXECUTION', 'RECOVERY')),
    acquired_at INTEGER NOT NULL CHECK (acquired_at >= 0),
    last_progress_at INTEGER NOT NULL CHECK (last_progress_at >= acquired_at),
    phase TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('ACTIVE', 'RECOVERY_PENDING', 'RELEASED')
    ),
    revision INTEGER NOT NULL CHECK (revision >= 1)
);

CREATE UNIQUE INDEX execution_leases_one_open_slot
ON execution_leases((1))
WHERE status IN ('ACTIVE', 'RECOVERY_PENDING');

CREATE INDEX execution_leases_by_task_run
ON execution_leases(task_id, run_id, acquired_at);
