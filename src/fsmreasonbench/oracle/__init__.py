"""Reference oracle library."""

from fsmreasonbench.oracle.reachability import (
    ReachabilityWitness,
    UnreachabilityWitness,
    is_reachable,
    reachable_states,
    shortest_reachability_witness,
    unreachability_witness,
)
from fsmreasonbench.oracle.simulation import SimulationResult, accepts_trace, simulate

__all__ = [
    "ReachabilityWitness",
    "SimulationResult",
    "UnreachabilityWitness",
    "accepts_trace",
    "is_reachable",
    "reachable_states",
    "shortest_reachability_witness",
    "simulate",
    "unreachability_witness",
]
