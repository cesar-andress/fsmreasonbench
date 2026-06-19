"""DFA minimization and equivalence hash tests."""

from fsmreasonbench.generator.separation import SeparationGeneratorConfig, generate_separation_dfa
from fsmreasonbench.generator.separation_equivalent import generate_equivalent_partner
from fsmreasonbench.runtime.dfa_minimize import complete_dfa, minimized_dfa_hash, minimize_dfa
from fsmreasonbench.oracle.separation import are_equivalent


def test_minimized_hashes_match_for_equivalent_partners() -> None:
    config = SeparationGeneratorConfig()
    fsm_a = complete_dfa(generate_separation_dfa(7, config, label="A", state_count=4))
    fsm_b = generate_equivalent_partner(fsm_a, 8)
    assert are_equivalent(fsm_a, fsm_b)
    assert minimized_dfa_hash(fsm_a) == minimized_dfa_hash(fsm_b)


def test_minimize_dfa_reduces_renamed_copy() -> None:
    config = SeparationGeneratorConfig()
    fsm_a = complete_dfa(generate_separation_dfa(11, config, label="A", state_count=4))
    renamed = generate_equivalent_partner(fsm_a, 12)
    mini_a = minimize_dfa(fsm_a)
    mini_b = minimize_dfa(renamed)
    assert mini_a.states == mini_b.states
    assert mini_a.accepting_states == mini_b.accepting_states
    assert len(mini_a.transitions) == len(mini_b.transitions)
