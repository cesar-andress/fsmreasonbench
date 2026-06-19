"""F1 generator and self-verification tests."""

from fsmreasonbench.generator.separation import generate_separation_item
from fsmreasonbench.items.assembly import self_verify_item
from fsmreasonbench.oracle.separation import are_equivalent


def test_generator_produces_self_verifying_f1_item() -> None:
    item = generate_separation_item(42)
    assert item.family == "F1"
    assert item.family_tier == "flagship"
    assert item.fsm_b is not None
    assert item.answer_key["verdict"] is False
    assert item.answer_key["certificate"]["certificate_type"] == "distinguishing_trace"
    assert not are_equivalent(item.fsm_a, item.fsm_b)
    self_verify_item(item)


def test_generator_records_difficulty_metadata() -> None:
    item = generate_separation_item(55)
    core = item.difficulty["core"]
    assert "|Q_A|" in core
    assert "|Q_B|" in core
    assert "distinguishing_trace_length" in core
    assert core["alphabet_size"] == len(item.fsm_a.input_alphabet)
