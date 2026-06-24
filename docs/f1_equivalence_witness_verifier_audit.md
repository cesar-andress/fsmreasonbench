# F1 equivalence_witness Verifier Audit

Hostile audit of the F1 equivalence witness verification path (no verifier changes).

## Code path

- **parser:** `src/fsmreasonbench/evaluator/parser.py::_validate_f1_certificate / _validate_equivalence_witness_payload`
- **scorer:** `src/fsmreasonbench/evaluator/scorer_f1.py::score_f1_item → verify_f1_certificate`
- **semantic_verifier:** `src/fsmreasonbench/verifier/separation.py::verify_equivalence_witness_certificate`
- **equivalence_check:** `src/fsmreasonbench/runtime/dfa_minimize.py::are_equivalent_dfas`
- **hash_computation:** `src/fsmreasonbench/runtime/dfa_minimize.py::minimized_dfa_hash`
- **certificate_builder:** `src/fsmreasonbench/certificates/separation.py::build_equivalence_witness_certificate`
- **error_taxonomy:** `src/fsmreasonbench/evaluator/failure_taxonomy.py::classify_certificate_errors`

## Acceptance condition

### Required fields
- certificate_type == equivalence_witness
- fsm_ids == [fsm_a.fsm_id, fsm_b.fsm_id]
- payload.equivalent == true
- payload.minimized_hash_A non-empty string
- payload.minimized_hash_B non-empty string

### Independently recomputed checks
- are_equivalent_dfas(fsm_a, fsm_b) must be True
- minimized_dfa_hash(fsm_a) compared to payload.minimized_hash_A
- minimized_dfa_hash(fsm_b) compared to payload.minimized_hash_B
- recomputed hashes must be equal

- **Single canonical witness form:** True
- **Alternative witness forms supported:** False
- **Hash mismatch implication:** When are_equivalent_dfas is True, hash mismatch means the declared witness does not match the verifier's recomputed language signature; it does NOT by itself prove non-equivalence.

### Certificate-contract limitations
- Only equivalence_witness with minimized_hash_A/B is accepted; no bijection table, no Hopcroft partition export, no distinguishing-trace negation proof.
- JSON schema file schema/certificate/separation.schema.json covers distinguishing_trace only; equivalence_witness is validated by evaluator parser + semantic verifier.
- Hash algorithm is fixed: content_hash of bounded language bitvector (trace lengths 0..min(|Q|,12) over reachable completed DFA).

## Audit checks

| ID | Title | Result | Detail |
|----|-------|--------|--------|
| A | Gold equivalence_witness passes | PASS | passed |
| B | Independently recomputed witness passes | PASS | passed |
| C | Correct verdict but wrong hash fails | PASS | passed |
| D | Gold hashes on non-equivalent pair fails semantically | PASS | passed |
| E | Non-equivalent pair with equivalence_witness fails | PASS | passed |
| F | Schema-valid irrelevant hashes fail | PASS | passed |
| G | Behavior-preserving equivalent pair passes after rebuild | PASS | passed |
| H | Alternative witness extras do not bypass hash contract | PASS | passed |
| I | Hash mismatch on equivalent pair is not labeled non-equivalent | PASS | passed |
| M_hash_a | mutate minimized_hash_A | PASS | passed |
| M_hash_b | mutate minimized_hash_B | PASS | passed |
| M_cert_type | mutate certificate_type | PASS | passed |
| M_fsm_ids | mutate fsm_ids | PASS | passed |
| M_equivalent_flag | mutate equivalent flag | PASS | passed |
| M_accepting | mutate accepting states rejects | PASS | passed |
| M_transition | mutate transitions rejects | PASS | passed |

**Summary:** 16/16 checks passed.

## Reviewer questions

### is checking semantic or purely canonical

Both. The verifier runs are_equivalent_dfas independently, then requires exact match to minimized_dfa_hash outputs. Semantic failure and hash mismatch are distinct.

### is verifier recomputing from supplied fsms

Yes. Equivalence and both hashes are recomputed from the benchmark FSM objects passed into verify_equivalence_witness_certificate; certificate hashes are never trusted alone.

### could claude zero be fragile hash format

Partially. Claude R1 eq-witness failures are taxonomy-labeled equivalence_hash_mismatch while verdict accuracy is 1.0, so models can be verdict-correct yet fail for not emitting the verifier's hash strings. That reflects the fixed witness contract, not JSON formatting. It is not merely canonical pedantry because non-equivalent pairs are rejected semantically before hash comparison when applicable.

### certificate contract limitations

Only hash-based equivalence_witness is accepted. No bijection/partition witnesses; separation.schema.json documents distinguishing_trace only.

### paper validity section sentence

See paper_validity_sentence in this audit JSON.

## Paper validity sentence

> An F1 equivalence_witness is valid iff the benchmark DFAs are semantically equivalent (independent BFS equivalence check) and the submitter supplies the exact minimized language-signature hashes recomputed by the verifier from those DFAs; hash mismatch rejects the witness format but is not, by itself, evidence of non-equivalence when the semantic check succeeds.

## Findings

- **No verifier bug found** in the audited path; behavior matches the documented contract.
- **Hash strictness is real** but paired with an independent semantic equivalence check.
- Claude's 0.000 eq-witness cert on R1 is consistent with **witness/hash construction failure** while verdicts remain correct; R2C uses `build_equivalence_witness_certificate`.
- **Reviewer concern partially valid:** `equivalence_hash_mismatch` does not prove the model refuted equivalence; it proves failure to emit the canonical hash witness required by the contract.
