"""Tests for certificate class complexity analysis export."""

from __future__ import annotations

from fsmreasonbench.evaluator.certificate_class_complexity_analysis import (
    CERTIFICATE_TYPES,
    build_comparative_matrix,
    run_certificate_class_complexity_analysis,
)
from fsmreasonbench.dev.doc_consistency import find_repo_root


def test_comparative_matrix_has_four_certificate_types():
    matrix = build_comparative_matrix()
    assert {row["certificate_type"] for row in matrix} == set(CERTIFICATE_TYPES)


def test_equivalence_witness_highest_complexity():
    matrix = {row["certificate_type"]: row for row in build_comparative_matrix()}
    eq = matrix["equivalence_witness"]["estimated_complexity_score"]
    for other in ("distinguishing_trace", "trace_witness", "unreachability_witness"):
        assert eq > matrix[other]["estimated_complexity_score"]


def test_analysis_includes_equivalence_hash_failures():
    payload = run_certificate_class_complexity_analysis(find_repo_root())
    pooled = payload["failure_taxonomy"]["pooled_by_certificate_type"]["equivalence_witness"]
    categories = {e["category"] for e in pooled["top_failure_categories"]}
    assert "equivalence_hash_mismatch" in categories
