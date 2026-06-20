"""Certificate schema excerpts for R1/R2 LLM track prompts."""

from __future__ import annotations

FINAL_SUBMISSION_ENVELOPE = """{
  "phase": "final_submission",
  "submission": {
    "item_id": "<must match item>",
    "verdict": true or false,
    "certificate": {
      "certificate_type": "<family-specific type>",
      "version": "1.0",
      "payload": { }
    }
  }
}"""

C2_TRACE_WITNESS_EXAMPLE = """{
  "certificate_type": "trace_witness",
  "version": "1.0",
  "fsm_id": "<fsm.fsm_id from item>",
  "verdict_supported": true,
  "payload": {
    "trace": ["b", "a"],
    "state_sequence": ["q0", "q2", "q3"],
    "accepting": true
  }
}"""

C2_UNREACHABILITY_WITNESS_EXAMPLE = """{
  "certificate_type": "unreachability_witness",
  "version": "1.0",
  "fsm_id": "<fsm.fsm_id from item>",
  "verdict_supported": false,
  "payload": {
    "reachable_states": ["q0", "q1", "q2"],
    "target_state": "q4"
  }
}"""

F1_DISTINGUISHING_TRACE_EXAMPLE = """{
  "certificate_type": "distinguishing_trace",
  "version": "1.0",
  "fsm_ids": ["<fsm_a.fsm_id>", "<fsm_b.fsm_id>"],
  "verdict_supported": false,
  "payload": {
    "trace": ["a", "b"],
    "acceptance": { "A": true, "B": false }
  }
}"""

F1_EQUIVALENCE_WITNESS_EXAMPLE = """{
  "certificate_type": "equivalence_witness",
  "version": "1.0",
  "fsm_ids": ["<fsm_a.fsm_id>", "<fsm_b.fsm_id>"],
  "verdict_supported": true,
  "payload": {
    "equivalent": true,
    "minimized_hash_A": "<64-char hex string>",
    "minimized_hash_B": "<64-char hex string>"
  }
}"""

INVALID_PAYLOAD_EXAMPLES = """INVALID (will fail extractability — do NOT emit):
- unreachability_witness.payload.reachable_states as string: "q0,q1"  ← must be JSON array
- trace as objects: [{"symbol":"a"}]  ← must be array of strings
- null symbol in trace: ["a", null, "b"]
- extra prose fields inside payload such as "reason" or "explanation"
- missing payload.reachable_states or payload.target_state for unreachability_witness
- missing payload.trace or payload.acceptance for distinguishing_trace"""

FINAL_SUBMISSION_CHECKLIST = """Before emitting final_submission, verify:
1. phase is exactly "final_submission"
2. submission.item_id equals the item_id in the prompt
3. submission.verdict is boolean (not string "true"/"false")
4. submission.certificate.certificate_type matches verdict and family rules
5. submission.certificate.version is "1.0"
6. submission.certificate.payload contains ONLY schema fields (no extra keys)
7. arrays are JSON arrays of strings where required (trace, state_sequence, reachable_states)
8. C2 verdict=true requires trace_witness; verdict=false requires unreachability_witness
9. F1 verdict=true requires equivalence_witness; verdict=false requires distinguishing_trace
10. Do not copy tool output objects wholesale into payload unless fields match the schema exactly"""

SCHEMA_RULE = (
    "RULE: final_submission.submission.certificate.payload fields must match the "
    "schema exactly. Extra keys, wrong types, or missing required fields cause "
    "extractability failure. The runner does not repair invalid submissions."
)

CERTIFICATE_EXAMPLES_BY_FAMILY = {
    "C2": (
        ("trace_witness (verdict=true)", C2_TRACE_WITNESS_EXAMPLE),
        ("unreachability_witness (verdict=false)", C2_UNREACHABILITY_WITNESS_EXAMPLE),
    ),
    "F1": (
        ("distinguishing_trace (verdict=false)", F1_DISTINGUISHING_TRACE_EXAMPLE),
        ("equivalence_witness (verdict=true)", F1_EQUIVALENCE_WITNESS_EXAMPLE),
    ),
}
