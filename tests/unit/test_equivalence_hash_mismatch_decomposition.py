"""Tests for equivalence hash mismatch decomposition."""

from __future__ import annotations

from fsmreasonbench.dev.doc_consistency import find_repo_root
from fsmreasonbench.evaluator.equivalence_hash_mismatch_decomposition import (
    decompose_equivalence_hash_mismatches,
    export_equivalence_hash_mismatch_decomposition,
)


def test_all_eq_witness_failures_classified():
    payload = decompose_equivalence_hash_mismatches(find_repo_root())
    assert payload["equivalence_item_count"] == 51
    assert payload["coverage"][0]["eq_witness_failures"] == 51
    assert payload["coverage"][1]["eq_witness_failures"] == 51
    assert payload["coverage"][0]["raw_response_available"] == 51


def test_semantic_claim_ok_on_most_failures():
    payload = decompose_equivalence_hash_mismatches(find_repo_root())
    pooled = payload["tables"]["C_noncanonical_proof_evidence"]["pooled"]
    assert pooled["semantic_claim_ok_count"] >= 100


def test_export_writes_docs_and_addendum():
    repo = find_repo_root()
    export_equivalence_hash_mismatch_decomposition(repo)
    assert (repo / "docs/equivalence_hash_mismatch_decomposition.json").exists()
    assert (
        repo / "docs/tmlr_empirical_package_v1/addendum_equivalence_hash_mismatch_decomposition.md"
    ).exists()
