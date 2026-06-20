"""Track evaluation package."""

from fsmreasonbench.tracks.agents import run_r0_agent, run_r1_agent, run_r2_agent
from fsmreasonbench.tracks.delegation import compute_delegation_gap
from fsmreasonbench.tracks.models import TrackId, TrackRunResult, TrackScoringRecord
from fsmreasonbench.tracks.replay import replay_audit_log
from fsmreasonbench.tracks.runner import run_track, run_track_batch

__all__ = [
    "TrackId",
    "TrackRunResult",
    "TrackScoringRecord",
    "compute_delegation_gap",
    "replay_audit_log",
    "run_r0_agent",
    "run_r1_agent",
    "run_r2_agent",
    "run_track",
    "run_track_batch",
]
