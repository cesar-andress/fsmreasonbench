"""Legacy boundary markers (immutable historical artifacts)."""

from __future__ import annotations

LEGACY_NAMESPACE = "legacy_v1"
CLEAN_NAMESPACE = "clean_v2"

LEGACY_CLASSIFICATION = {
    "frontier_r1_outputs": "C_diagnostic",
    "oracle_plus_format": "D_invalid_causal_C_diagnostic",
    "a1_constructible": "C_diagnostic",
    "r2c_ablations": "D_as_model_A_as_sys_ceiling",
    "digest_cells": "C_infeasibility_control",
    "mixed_gap_tables": "D_not_clean_v2_evidence",
    "item_manifests": "A_usable_structure",
    "gold_answer_keys": "A_evaluator_only",
}

IMMUTABLE_RUN_ROOTS = (
    "runs/frontier_claude_sonnet_tools_n100_v2",
    "runs/frontier_gpt_tools_n100_v1",
    "runs/ablations_f1_r2_attribution_claude_n100_v1",
    "runs/ablations_f1_oracle_verdict_format_control_claude_n100_v1",
    "runs/f1_constructible_equivalence_claude_n100_v1",
    "runs/f1_constructible_equivalence_gpt_n100_v1",
    "runs/local_matrix_n100_t02_v2",
)

DERIVED_RESCORE_ROOT = "runs/clean_v2_derived_rescores"
