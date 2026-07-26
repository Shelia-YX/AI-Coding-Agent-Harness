from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


VECTOR_IDS = {
    "genesis-minimal",
    "genesis-multi",
    "continuation-single-entry",
}
ROOT_FIELDS = [
    "identity",
    "revision",
    "baseline_digest",
    "approval_intent_digest",
    "workspace_logical_identity",
    "exportable_to_llm",
    "entries",
]
ENTRY_FIELDS = [
    "path",
    "kind",
    "size",
    "content_digest",
    "mode",
    "allowed_stages",
    "changeset_eligible",
    "writeback_permitted",
    "exportable_to_llm",
]
MUTATION_FIELDS = {
    *(f"root.{name}" for name in ROOT_FIELDS[:-1]),
    *(f"entry.{name}" for name in ENTRY_FIELDS),
}


class FixtureValidationError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FixtureValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise FixtureValidationError(f"non-finite JSON number: {value}")


def _load_json(path: Path) -> Any:
    try:
        text = path.read_bytes().decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FixtureValidationError(f"invalid fixture JSON: {path.name}") from error
    _reject_non_finite(value)
    return value


def _reject_non_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise FixtureValidationError("non-finite JSON number")
    if isinstance(value, dict):
        for child in value.values():
            _reject_non_finite(child)
    elif isinstance(value, list):
        for child in value:
            _reject_non_finite(child)


def _require_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise FixtureValidationError(f"{label} schema keys do not match")


def _hex_digest(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value.lower() != value
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise FixtureValidationError(f"{label} is not lowercase SHA-256 hex")
    return value


def _validate_span(raw: bytes, value: dict[str, Any]) -> tuple[int, int]:
    _require_keys(
        value,
        {"offset", "byte_length", "field_name", "encoded_bytes"},
        "annotation span",
    )
    start = value["offset"]
    length = value["byte_length"]
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(length, int)
        or isinstance(length, bool)
        or start < 0
        or length <= 0
    ):
        raise FixtureValidationError("invalid annotation span bounds")
    end = start + length
    if raw[start:end].hex() != value["encoded_bytes"]:
        raise FixtureValidationError("annotation bytes do not match canonical stream")
    return start, end


def _validate_partition(
    raw: bytes, spans: list[dict[str, Any]], start: int, end: int
) -> None:
    cursor = start
    for value in spans:
        span_start, span_end = _validate_span(raw, value)
        if span_start != cursor:
            raise FixtureValidationError("annotation gap or overlap")
        cursor = span_end
    if cursor != end:
        raise FixtureValidationError("annotation trailing bytes")


def _validate_vectors(
    inputs: dict[str, Any], outputs: dict[str, Any]
) -> dict[str, bytes]:
    _require_keys(inputs, {"schema", "vectors"}, "vector input")
    if inputs["schema"] != "wp11-manifest-digest-v1-candidate-input:1":
        raise FixtureValidationError("unexpected vector input schema")
    _require_keys(outputs, {"vectors"}, "vector output")
    input_ids = {item["id"] for item in inputs["vectors"]}
    if input_ids != VECTOR_IDS:
        raise FixtureValidationError("unexpected input vector IDs")

    streams: dict[str, bytes] = {}
    for vector in outputs["vectors"]:
        _require_keys(vector, {"id", "raw_hex", "length", "sha256"}, "vector")
        vector_id = vector["id"]
        if vector_id in streams or vector_id not in VECTOR_IDS:
            raise FixtureValidationError("duplicate or unexpected output vector ID")
        try:
            raw = bytes.fromhex(vector["raw_hex"])
        except ValueError as error:
            raise FixtureValidationError("invalid canonical stream hex") from error
        if vector["raw_hex"] != raw.hex():
            raise FixtureValidationError("canonical stream hex is not normalized")
        if vector["length"] != len(raw):
            raise FixtureValidationError("canonical stream length mismatch")
        if _hex_digest(vector["sha256"], "vector digest") != hashlib.sha256(
            raw
        ).hexdigest():
            raise FixtureValidationError("canonical stream digest mismatch")
        streams[vector_id] = raw
    if set(streams) != VECTOR_IDS:
        raise FixtureValidationError("missing output vector")
    return streams


def _validate_annotations(
    document: dict[str, Any], streams: dict[str, bytes]
) -> None:
    _require_keys(document, {"vectors"}, "annotation document")
    seen: set[str] = set()
    for vector in document["vectors"]:
        _require_keys(
            vector,
            {
                "id",
                "length",
                "sha256",
                "top_level",
                "root_fields",
                "entries",
                "validation",
            },
            "annotated vector",
        )
        vector_id = vector["id"]
        if vector_id in seen or vector_id not in streams:
            raise FixtureValidationError("duplicate or unexpected annotated vector")
        seen.add(vector_id)
        raw = streams[vector_id]
        if vector["length"] != len(raw):
            raise FixtureValidationError("annotated length mismatch")
        if vector["sha256"] != hashlib.sha256(raw).hexdigest():
            raise FixtureValidationError("annotated digest mismatch")
        _validate_partition(raw, vector["top_level"], 0, len(raw))
        if [item["field_name"] for item in vector["root_fields"]] != ROOT_FIELDS:
            raise FixtureValidationError("root annotation fields do not match schema")
        root_bounds = [_validate_span(raw, item) for item in vector["root_fields"]]
        for left, right in zip(root_bounds, root_bounds[1:]):
            if left[1] != right[0]:
                raise FixtureValidationError("root field gap or overlap")
        for entry in vector["entries"]:
            _require_keys(
                entry,
                {"offset", "byte_length", "field_name", "encoded_bytes", "fields"},
                "annotated entry",
            )
            entry_start, entry_end = _validate_span(
                raw, {key: entry[key] for key in entry if key != "fields"}
            )
            if [item["field_name"] for item in entry["fields"]] != ENTRY_FIELDS:
                raise FixtureValidationError("entry annotation fields do not match schema")
            bounds = [_validate_span(raw, item) for item in entry["fields"]]
            if not (entry_start < bounds[0][0] and bounds[-1][1] == entry_end):
                raise FixtureValidationError("entry annotation bounds mismatch")
            for left, right in zip(bounds, bounds[1:]):
                if left[1] != right[0]:
                    raise FixtureValidationError("entry field gap or overlap")
        expected_validation = {
            "top_level_no_gap_or_overlap": True,
            "root_no_gap_or_overlap": True,
            "entries_no_gap_or_overlap": True,
            "trailing_bytes": 0,
        }
        if vector["validation"] != expected_validation:
            raise FixtureValidationError("annotation validation flags mismatch")
    if seen != VECTOR_IDS:
        raise FixtureValidationError("missing annotated vector")


def _validate_mutations(document: dict[str, Any]) -> tuple[int, int]:
    _require_keys(
        document,
        {"baseline_digest", "baseline_vector", "coverage", "mutations"},
        "mutation document",
    )
    _hex_digest(document["baseline_digest"], "mutation baseline digest")
    fields = {item["field"] for item in document["mutations"]}
    if fields != MUTATION_FIELDS or len(document["mutations"]) != len(fields):
        raise FixtureValidationError("mutation field coverage mismatch")
    for item in document["mutations"]:
        _require_keys(
            item,
            {
                "field",
                "baseline_digest",
                "mutated_digest",
                "changed",
                "encoder_a_oracle_b_equal",
            },
            "mutation",
        )
        baseline = _hex_digest(item["baseline_digest"], "mutation baseline")
        mutated = _hex_digest(item["mutated_digest"], "mutation result")
        if baseline != document["baseline_digest"]:
            raise FixtureValidationError("mutation baseline mismatch")
        if item["changed"] is not True or baseline == mutated:
            raise FixtureValidationError("mutation did not change digest")
        if item["encoder_a_oracle_b_equal"] is not True:
            raise FixtureValidationError("mutation encoders disagree")
    if document["coverage"] != {
        "all_changed": True,
        "encoder_a_oracle_b_equal": True,
        "entry_fields": 9,
        "root_fields": 6,
    }:
        raise FixtureValidationError("mutation coverage summary mismatch")
    return 6, 9


def _validate_invariance(document: dict[str, Any]) -> None:
    _require_keys(
        document,
        {
            "canonical_stream_identical",
            "digest_a",
            "digest_b",
            "digest_identical",
            "encoder_a_oracle_b_equal",
            "input_order_a",
            "input_order_b",
        },
        "invariance document",
    )
    digest_a = _hex_digest(document["digest_a"], "invariance digest A")
    digest_b = _hex_digest(document["digest_b"], "invariance digest B")
    if document["input_order_a"] != ["ignored/z.txt", "ignored/a.txt"]:
        raise FixtureValidationError("unexpected invariance input order A")
    if document["input_order_b"] != ["ignored/a.txt", "ignored/z.txt"]:
        raise FixtureValidationError("unexpected invariance input order B")
    if (
        document["canonical_stream_identical"] is not True
        or document["digest_identical"] is not True
        or document["encoder_a_oracle_b_equal"] is not True
        or digest_a != digest_b
    ):
        raise FixtureValidationError("ordering invariance evidence mismatch")


def _validate_provenance(root: Path, document: dict[str, Any]) -> None:
    _require_keys(
        document,
        {
            "fixture_schema",
            "candidate_root",
            "review_status",
            "source_artifacts",
            "repository_artifacts",
        },
        "provenance document",
    )
    if (
        document["fixture_schema"] != "wp11-manifest-digest-v1-evidence:1"
        or document["review_status"] != "PASS"
    ):
        raise FixtureValidationError("provenance status mismatch")
    for filename, expected in document["repository_artifacts"].items():
        _hex_digest(expected, f"provenance digest for {filename}")
        actual = hashlib.sha256((root / filename).read_bytes()).hexdigest()
        if actual != expected:
            raise FixtureValidationError(f"provenance mismatch: {filename}")
    for filename, digest in document["source_artifacts"].items():
        _hex_digest(digest, f"source provenance digest for {filename}")


def load_and_validate(root: Path) -> dict[str, object]:
    inputs = _load_json(root / "wp11_manifest_digest_v1_vectors.input.json")
    outputs = _load_json(root / "wp11_manifest_digest_v1_vectors.json")
    offsets = _load_json(root / "wp11_manifest_digest_v1_offsets.json")
    mutations = _load_json(root / "wp11_manifest_digest_v1_mutations.json")
    invariance = _load_json(root / "wp11_manifest_digest_v1_invariance.json")
    provenance = _load_json(root / "wp11_manifest_digest_v1_provenance.json")

    streams = _validate_vectors(inputs, outputs)
    _validate_annotations(offsets, streams)
    root_mutations, entry_mutations = _validate_mutations(mutations)
    _validate_invariance(invariance)
    _validate_provenance(root, provenance)
    return {
        "vectors": len(streams),
        "annotated_vectors": len(offsets["vectors"]),
        "root_mutations": root_mutations,
        "entry_mutations": entry_mutations,
        "ordering_invariant": True,
        "provenance_verified": True,
    }
