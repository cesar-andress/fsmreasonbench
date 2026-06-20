"""Reference baselines for benchmark calibration."""

from fsmreasonbench.baselines.c2 import (
    run_invalid_baseline,
    run_oracle_baseline,
    run_random_baseline,
)
from fsmreasonbench.baselines.competent_submitter import (
    build_competent_submission,
    run_competent_submitter,
)
from fsmreasonbench.baselines.reference_submitter import (
    build_reference_submission,
    run_reference_submitter,
)

__all__ = [
    "build_competent_submission",
    "build_reference_submission",
    "run_competent_submitter",
    "run_invalid_baseline",
    "run_oracle_baseline",
    "run_random_baseline",
    "run_reference_submitter",
]
