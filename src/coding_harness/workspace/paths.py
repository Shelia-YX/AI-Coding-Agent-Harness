"""Repository-root-relative path identities.

This module is deliberately lexical.  Physical containment belongs to
``workspace.file_model.inspect_supported_entry`` and must be checked again by
the eventual execution owner at use time.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import unicodedata
from typing import Iterable


_MAX_ENCODED_PATH_BYTES = 4095
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
_GLOB_MARKERS = frozenset("*?[")
_INVALID_MESSAGE = "repository path is invalid"


def _fail() -> ValueError:
    return ValueError(_INVALID_MESSAGE)


def _canonicalize(value: object) -> tuple[str, tuple[str, ...]]:
    if type(value) is not str:
        raise _fail()
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeError:
        raise _fail() from None
    if not value or len(encoded) > _MAX_ENCODED_PATH_BYTES:
        raise _fail()
    if unicodedata.normalize("NFKC", value) != value:
        raise _fail()
    if any(unicodedata.category(character).startswith("C") for character in value):
        raise _fail()
    if (
        value.startswith(("/", "\\"))
        or "\\" in value
        or _WINDOWS_DRIVE.match(value) is not None
        or value.endswith("/")
    ):
        raise _fail()

    segments = tuple(value.split("/"))
    if any(
        not segment
        or segment in {".", ".."}
        or segment.startswith(("-", ":"))
        or any(marker in segment for marker in _GLOB_MARKERS)
        for segment in segments
    ):
        raise _fail()

    canonical = "/".join(segments)
    if canonical != value:
        raise _fail()
    return canonical, segments


@dataclass(frozen=True, slots=True)
class RepoPath:
    """An immutable canonical repository-relative path."""

    canonical: str
    segments: tuple[str, ...]
    identity: str
    display_name: str

    @classmethod
    def parse(cls, value: object) -> "RepoPath":
        canonical, segments = _canonicalize(value)
        identity = hashlib.sha256(
            b"coding-harness:repo-path:v1\0" + canonical.encode("utf-8")
        ).hexdigest()
        return cls(
            canonical=canonical,
            segments=segments,
            identity=identity,
            display_name=canonical,
        )

    @classmethod
    def from_segments(cls, segments: Iterable[object]) -> "RepoPath":
        if isinstance(segments, (str, bytes)):
            raise _fail()
        try:
            copied = tuple(segments)
        except (TypeError, ValueError):
            raise _fail() from None
        if not copied or any(type(segment) is not str for segment in copied):
            raise _fail()
        return cls.parse("/".join(copied))

    def __post_init__(self) -> None:
        canonical, segments = _canonicalize(self.canonical)
        expected_identity = hashlib.sha256(
            b"coding-harness:repo-path:v1\0" + canonical.encode("utf-8")
        ).hexdigest()
        if (
            type(self.segments) is not tuple
            or self.segments != segments
            or type(self.identity) is not str
            or self.identity != expected_identity
            or type(self.display_name) is not str
            or self.display_name != canonical
        ):
            raise _fail()

    def __bool__(self) -> bool:
        raise TypeError("RepoPath has no truth value")
