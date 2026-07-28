"""Strict, forward-only SQLite schema migrations."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import sqlite3
import time


_MIGRATION_NAME = re.compile(r"^(?P<version>[0-9]{3,})_(?P<name>[a-z0-9_]+)\.sql$")


class MigrationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _Migration:
    version: int
    name: str
    checksum: str
    sql: str


def _statements(script: str) -> tuple[str, ...]:
    statements: list[str] = []
    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            statement = pending.strip()
            if statement:
                statements.append(statement)
            pending = ""
    if pending.strip():
        raise MigrationError("migration contains incomplete SQL")
    return tuple(statements)


class MigrationRunner:
    def __init__(
        self,
        *,
        database_path: Path,
        migration_directory: Path,
    ) -> None:
        if not isinstance(database_path, Path) or not isinstance(
            migration_directory, Path
        ):
            raise ValueError("migration runner is invalid")
        self._database_path = database_path
        self._migration_directory = migration_directory

    def _discover(self) -> tuple[_Migration, ...]:
        try:
            entries = tuple(self._migration_directory.iterdir())
        except OSError:
            raise MigrationError("migration directory is unavailable") from None
        migrations: list[_Migration] = []
        for path in entries:
            match = _MIGRATION_NAME.fullmatch(path.name)
            if match is None:
                if path.is_file() and path.suffix == ".sql":
                    raise MigrationError("migration filename is invalid")
                continue
            try:
                content = path.read_bytes()
                sql = content.decode("utf-8", errors="strict")
            except (OSError, UnicodeError):
                raise MigrationError("migration cannot be read") from None
            migrations.append(
                _Migration(
                    version=int(match.group("version")),
                    name=match.group("name"),
                    checksum=hashlib.sha256(content).hexdigest(),
                    sql=sql,
                )
            )
        migrations.sort(key=lambda item: item.version)
        versions = tuple(item.version for item in migrations)
        if versions != tuple(range(1, len(migrations) + 1)):
            raise MigrationError("migration versions are not strictly ordered")
        return tuple(migrations)

    def run(self) -> None:
        migrations = self._discover()
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            connection = sqlite3.connect(
                self._database_path,
                isolation_level=None,
                timeout=0,
            )
        except sqlite3.Error:
            raise MigrationError("migration database is unavailable") from None
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations("
                "version INTEGER PRIMARY KEY,"
                "name TEXT NOT NULL,"
                "checksum TEXT NOT NULL,"
                "applied_at INTEGER NOT NULL)"
            )
            applied = connection.execute(
                "SELECT version, name, checksum "
                "FROM schema_migrations ORDER BY version"
            ).fetchall()
            if any(
                type(version) is not int
                or version < 1
                or version > len(migrations)
                for version, _, _ in applied
            ):
                raise MigrationError(
                    "database version is incompatible; no downgrade is allowed"
                )
            applied_versions_in_order = tuple(row[0] for row in applied)
            if applied_versions_in_order != tuple(
                range(1, len(applied) + 1)
            ):
                raise MigrationError(
                    "migration history is not a contiguous prefix"
                )
            for version, name, checksum in applied:
                expected = migrations[version - 1]
                if name != expected.name or checksum != expected.checksum:
                    raise MigrationError("migration checksum drift detected")
            applied_versions = {row[0] for row in applied}
            for migration in migrations:
                if migration.version in applied_versions:
                    continue
                for statement in _statements(migration.sql):
                    connection.execute(statement)
                connection.execute(
                    "INSERT INTO schema_migrations"
                    "(version, name, checksum, applied_at) VALUES(?, ?, ?, ?)",
                    (
                        migration.version,
                        migration.name,
                        migration.checksum,
                        time.time_ns(),
                    ),
                )
            connection.execute("COMMIT")
        except MigrationError:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        except sqlite3.Error:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise MigrationError("migration failed") from None
        finally:
            connection.close()


__all__ = ["MigrationError", "MigrationRunner"]
