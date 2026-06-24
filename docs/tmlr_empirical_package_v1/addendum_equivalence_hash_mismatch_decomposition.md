# Addendum: equivalence hash mismatch decomposition

See full analysis: `docs/equivalence_hash_mismatch_decomposition.md`

# Equivalence Witness Hash Mismatch Decomposition

Construct-validity subtypes for Claude F1 `equivalence_witness` failures. **No new model calls; frozen runs only.**

## Coverage

### R1 frozen

- results coverage: 51/51
- scores coverage: 51/51
- transcripts present: 51/51
- raw responses available: 51/51
- eq-witness failures: 51

### Oracle+Format

- results coverage: 51/51
- scores coverage: 51/51
- transcripts present: 51/51
- raw responses available: 51/51
- eq-witness failures: 51

## Table A — Category counts

### R1

| category | count | percentage |
|----------|------:|-----------:|
| C1_EMPTY_OR_PLACEHOLDER | 13 | 0.255 |
| C2_RANDOM_OR_NONMATCHING_HASH | 1 | 0.020 |
| C5_EQUAL_BUT_WRONG_SHARED_HASH | 29 | 0.569 |
| C6_NONCANONICAL_STRUCTURAL_PROOF | 8 | 0.157 |

### Oracle+Format

| category | count | percentage |
|----------|------:|-----------:|
| C1_EMPTY_OR_PLACEHOLDER | 49 | 0.961 |
| C5_EQUAL_BUT_WRONG_SHARED_HASH | 2 | 0.039 |

### pooled

| category | count | percentage |
|----------|------:|-----------:|
| C1_EMPTY_OR_PLACEHOLDER | 62 | 0.608 |
| C2_RANDOM_OR_NONMATCHING_HASH | 1 | 0.010 |
| C5_EQUAL_BUT_WRONG_SHARED_HASH | 31 | 0.304 |
| C6_NONCANONICAL_STRUCTURAL_PROOF | 8 | 0.078 |

## Table B — Hash pattern analysis

### R1
- **n_failures:** 51
- **hash_missing_or_placeholder_rate:** 0.255
- **hash_like_but_wrong_rate:** 0.745
- **one_hash_correct_rate:** 0.0
- **swapped_rate:** 0.0
- **equal_but_wrong_shared_hash_rate:** 0.569

### Oracle+Format
- **n_failures:** 51
- **hash_missing_or_placeholder_rate:** 0.961
- **hash_like_but_wrong_rate:** 0.039
- **one_hash_correct_rate:** 0.0
- **swapped_rate:** 0.0
- **equal_but_wrong_shared_hash_rate:** 0.039

### pooled
- **n_failures:** 102
- **hash_missing_or_placeholder_rate:** 0.608
- **hash_like_but_wrong_rate:** 0.392
- **one_hash_correct_rate:** 0.0
- **swapped_rate:** 0.0
- **equal_but_wrong_shared_hash_rate:** 0.304

## Table C — Non-canonical proof evidence

### R1
- **primary_c6_count:** 8
- **semantic_claim_ok_count:** 51
- **signal_counts:**
  - language_argument: 24
  - step_replay_argument: 4
  - minimized_automaton: 11
- **state_mapping_responses:** 0
- **partition_like_responses:** 0
- **minimized_automaton_mentions:** 11
- **language_argument_responses:** 24
- **machine_checkable_under_broader_verifier:** No submitted response included a standalone machine-checkable alternate witness object (partition table, bisimulation relation, or mapping) in the certificate payload; prose arguments might support a richer verifier but were not encoded as checkable artifacts.

### Oracle+Format
- **primary_c6_count:** 0
- **semantic_claim_ok_count:** 51
- **signal_counts:**
- **state_mapping_responses:** 0
- **partition_like_responses:** 0
- **minimized_automaton_mentions:** 0
- **language_argument_responses:** 0
- **machine_checkable_under_broader_verifier:** No submitted response included a standalone machine-checkable alternate witness object (partition table, bisimulation relation, or mapping) in the certificate payload; prose arguments might support a richer verifier but were not encoded as checkable artifacts.

### pooled
- **primary_c6_count:** 8
- **semantic_claim_ok_count:** 102
- **signal_counts:**
  - language_argument: 24
  - step_replay_argument: 4
  - minimized_automaton: 11
- **state_mapping_responses:** 0
- **partition_like_responses:** 0
- **minimized_automaton_mentions:** 11
- **language_argument_responses:** 24
- **machine_checkable_under_broader_verifier:** No submitted response included a standalone machine-checkable alternate witness object (partition table, bisimulation relation, or mapping) in the certificate payload; prose arguments might support a richer verifier but were not encoded as checkable artifacts.

## Research answers

### mostly_empty_or_fake_hashes

No for R1 frozen: only 13/51 are empty/placeholder/non-hex (29/51 are equal-but-wrong-shared-hash with hash-like hex). Oracle+Format shows more placeholder/template behavior (49/51 C1; 2/51 C5).

### semantically_plausible_noncanonical_proofs

Prose contains language/step-replay arguments in many failures, but no certificate payload encodes an alternate machine-checkable witness. Primary C6 count (structured alternate proof as main failure mode): 8 across pooled failures.

### zero_rate_interpretation

102/102 pooled failures keep a semantically correct equivalence claim (verdict true, equivalent true, correct certificate type) yet fail verifier hash equality. The 0.000 cert rate primarily measures failure to emit verifier-identical minimized_dfa_hash strings, not rejection of valid alternate proof objects in the certificate schema.

### justified_thesis_sentence

Claude accepts equivalence verdicts but cannot synthesize verifier-identical minimized_dfa_hash witnesses under R1/Oracle; failures are dominated by wrong-hash emission patterns while semantic equivalence claims remain correct.

### too_strong_thesis_sentence

Claiming Claude cannot reason about DFA equivalence at all, or that failures prove misunderstood non-equivalence, or that a generic universal-quantifier deficit explains F1.

### limitations_section

Equivalence_witness verification accepts only minimized_dfa_hash strings; natural-language or step-simulation arguments in prose are not scored. This decomposition classifies hash-construction patterns from frozen parsed payloads plus raw_response_text in results.jsonl (transcripts present but not required). Subtype labels are heuristic; C6 requires substantive structured alternate-proof language and remains rare relative to wrong-hash emission (C5/C1/C2).

## Examples (safe excerpts)

### C5_EQUAL_BUT_WRONG_SHARED_HASH
- `c3ee241b-d418-568b-b476-b6cf390cb2cc` (R1): Looking at the tool execution results, I can see that both FSMs were stepped through identical input sequences and produced identical state transitions:  - Both started at q0 - Both transitioned q0 --a--> q2 - Both transitioned q2 --a--> q1 - Both stayed at q1 on 'b' inputs - Both transitioned q1 --c--> q0 - Both tr...
- `527be1ca-c15b-5469-8d2b-e3b25bc9883a` (R1): ```json | hash_A=f7529c7209b82913... hash_B=f7529c7209b82913... gold=8ee9bbae7cbf8d71...
- `e8dcdee7-a977-5365-a166-9723ac71423a` (R1): Looking at the tool execution results, I need to analyze whether FSM A and FSM B are equivalent.  From the tool results, I can see that I systematically tested various input sequences on both FSMs:  1. Input "a": q0→q2 (A), alt_q0→alt_q2 (B) - both reach non-accepting states 2. Input "c": q0→q1 (A), alt_q0→alt_q1 (B...

### C1_EMPTY_OR_PLACEHOLDER
- `a6f510b5-ceea-5cbe-98b2-2876be119a7d` (R1): hash_A='0b420da2-7c66-5bd2-922b-ccf150c6f890-minimized-canonical-form' hash_B='0b420da2-7c66-5bd2-922b-ccf150c6f890-minimized-canonical-form' gold_A=02e5f3c7a6202c1e... gold_B=02e5f3c7a6202c1e...
- `d7f6fc21-4a31-504b-b50a-685f90a24bda` (R1): hash_A='0000000000000000000000000000000000000000000000000000000000000000' hash_B='0000000000000000000000000000000000000000000000000000000000000000' gold_A=d8a97269ba57acdc... gold_B=d8a97269ba57acdc...
- `32e3ad12-2354-5078-ba55-5862323c8844` (R1): hash_A='a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2' hash_B='a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2' gold_A=fc845df0d2bdb080... gold_B=fc845df0d2bdb080...

### C6_NONCANONICAL_STRUCTURAL_PROOF
- `f86f7dd4-150d-55b4-a9b0-6577ecf9fe92` (R1): Looking at the tool execution results, I need to analyze whether FSM A and FSM B are equivalent.  From the tool results, I can see that for each pair of step calls (odd-numbered call for FSM A, even-numbered call for FSM B), both FSMs transition to the same next state given the same input sequence. This suggests the...
- `06d801e1-67d3-52b6-a717-29ba68b012b3` (R1): Looking at the tool execution results, I need to analyze whether FSM A and FSM B are equivalent.  From the item metadata, I can see: - `"equivalent": true` in the difficulty.core section - FSM B has metadata indicating `"equivalent_transform": "unreachable"`, meaning it has an unreachable state but is otherwise equi...
- `6ec2a350-88e4-5282-8374-efad6de9221c` (R1): Looking at the tool execution results, I need to analyze whether FSM A and FSM B are equivalent.  From the tool results, I can see that the execution traced through various states in both FSMs: - Both FSMs transitioned identically through corresponding states (q0↔prime_q0, q1↔prime_q1, q2↔prime_q2, q3↔prime_q3, __tr...

### C2_RANDOM_OR_NONMATCHING_HASH
- `a774a8ac-34ed-5c1e-976f-427f45e7d6a6` (R1): ```json | hash_A=8b819e37d38955bd... hash_B=f42335618e3a5f31... gold=d3aeba8ca3c29712...
