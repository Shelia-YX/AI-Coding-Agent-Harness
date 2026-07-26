from __future__ import annotations

import importlib.util
from pathlib import Path


FIXTURE_ROOT = Path(__file__).parents[2] / "fixtures" / "workspace"
LOADER_PATH = FIXTURE_ROOT / "wp11_manifest_digest_v1_loader.py"


def test_wp11_manifest_digest_v1_evidence_is_strict_and_self_consistent() -> None:
    spec = importlib.util.spec_from_file_location(
        "wp11_manifest_digest_v1_loader", LOADER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    result = module.load_and_validate(FIXTURE_ROOT)

    assert result == {
        "vectors": 3,
        "annotated_vectors": 3,
        "root_mutations": 6,
        "entry_mutations": 9,
        "ordering_invariant": True,
        "provenance_verified": True,
    }
