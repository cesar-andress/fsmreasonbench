# PRE_SPECIFICATION — clean_v2 confirmatory campaign

**Status:** FROZEN before any confirmatory or pilot model generation.  
**spec_version:** `clean_v2.confirmatory.v1`  
**spec_frozen_at:** `2026-09-02T13:00:48Z`  
**harness_commit_at_freeze_draft:** `6009e44f4d26c4a676b065eb930c165e34a3752f`  
**analysis_commit_at_freeze_draft:** `6009e44f4d26c4a676b065eb930c165e34a3752f` (same tree; confirmatory analysis under `src/fsmreasonbench/clean_v2/confirmatory/`)  
**freeze_git_tag_placeholder:** `clean_v2-confirmatory-prespec-v1` (annotate after commit)  
**cohort_fingerprint:** `61f1ccaa4bf2927361e140b239ac5aaccf8a1c0ab2370f8f915e13e17b06af9b`  
**execution_order_seed:** `20260902`  
**bootstrap_seed:** `424242`  
**permutation_seed:** `1357911`

This document is the confirmatory pre-data specification. It remains scientifically valid if every experimental effect is null. It does not optimize for significance.

---

## Identification

| Field | Value |
|---|---|
| spec_version | clean_v2.confirmatory.v1 |
| timestamp | 2026-09-02T13:00:48Z |
| harness commit | 6009e44f4d26c4a676b065eb930c165e34a3752f (freeze landing commit) |
| analysis commit | same |
| experiment fingerprints | see `docs/clean_v2/manifests/` condition_fingerprint fields |
| freeze git tag | `clean_v2-confirmatory-prespec-v1` (placeholder until annotated) |

---

## Research questions (verbatim for this campaign)

### RQ1 (descriptive; no hypothesis test)

On the frozen 100-item F1 cohort, under contract=`bisimulation`, tool_palette=`T1_STEP`, oracle=`none`, format=`off`, for each pinned model snapshot separately: what is the composition of generations over `n_attempted` across extraction failure, wrong verdict, correct verdict with invalid witness, and fully correct? Separately, what is verdict performance on the near-balanced 100-item universe, and what is the equivalent-response bias on the 49 distinguishing items?

### RQ2 (confirmatory; contract sensitivity)

For equivalence items only (n=51), holding tool_palette=`T1_STEP`, oracle=`none`, format=`off`, and model snapshot fixed: does changing the witness contract from `bisimulation` to `minimized_dfa` change the item-level rate of `witness_valid`?

### RQ3 (confirmatory; non-answer-producing tool support)

For equivalence items only (n=51), holding contract=`bisimulation`, oracle=`none`, format=`off`, and model snapshot fixed: does changing the tool palette among `T0_NONE`, `T1_STEP`, and `T3_VERIFY` change the item-level rate of `witness_valid`? Primary contrasts are T0 vs T1 and T1 vs T3. For T1 vs T3, `witness_valid_first` is a co-primary diagnostic distinguishing first-proposal construction from verifier-guided search.

---

## Hypotheses / intended contrasts

### Primary (per model; Holm family of 3)

1. RQ2: mean paired risk difference for `witness_valid`: bisimulation_T1 − minimized_dfa_T1.
2. RQ3: mean paired RD for `witness_valid`: bisimulation_T1 − bisimulation_T0.
3. RQ3: mean paired RD for `witness_valid`: bisimulation_T3 − bisimulation_T1.

### Co-primary diagnostic (T1→T3 only)

4. Intersection rule: stronger "improved witness construction" requires material improvement on both final `witness_valid` and `witness_valid_first` (see Falsification).

### Secondary

5. RQ3: T0 vs T3 for `witness_valid` (estimation; not in Holm family).
6. Cross-model difference of model-specific paired RDs (interval only; no confirmatory interaction test).
7. RQ2 verdict negative control on `verdict_correct` (manipulation validity; not a verdict performance claim).

### Explicitly non-confirmatory

- All RQ1 quantities.
- `verdict_correct` on the 51 equivalence-only items (pipeline diagnostic only).
- `P(witness_valid | verdict_correct)` and `P(witness_valid | extractable)` (descriptive; print denominators; never hypothesis-tested).
- Contract burden metrics (size, field counts, etc.).

---

## Scope of inference

Inferential statements are limited to:

- the two exact pinned snapshots listed under Models;
- the frozen item generator/cohort listed under Items;
- the exact contracts and tool conditions listed under Conditions;
- the exact harness/analysis fingerprints and this spec_version.

**No statement may generalize to LLMs in general.** Models are a fixed factor with two observed snapshots, not a random effect. Cross-model agreement is conceptual replication only.

---

## Items

| Field | Value |
|---|---|
| generator | `fsmreasonbench.generator.separation` |
| mode | `constructive_decoy` |
| equivalent_ratio | 0.5 |
| distinguishing_trace_length | min=3, max=3 |
| seed_start–seed_end | 203001–203100 |
| cohort_id | `f1-mixed-level3-v0.1-expanded-n100` |
| cohort_fingerprint | `61f1ccaa4bf2927361e140b239ac5aaccf8a1c0ab2370f8f915e13e17b06af9b` |
| generator commit at cohort creation | `76d221295f8fc7dd50235acfa2928c1b6d96b131` |
| reproducible | yes (deterministic local generator + frozen files) |
| outcome-dependent selection | **No** |
| decision | **`REUSE_ALL_51`** (reuse all 51 equivalence items; do not subset) |

Full provenance answers: `docs/clean_v2/ITEM_PROVENANCE_AUDIT.json`.

### Public exposure

- Artifact release date (ARTIFACT_VERSION): 2026-06-20
- Cohort created_at: 2026-06-22T02:26:04Z
- Zenodo DOI: 10.5281/zenodo.20897937
- Model snapshots post-date public item availability.

### Equivalence item IDs (n=51)

- `0027e8d7-4960-5973-8266-d7b17f673831`
- `05f2e4ef-d67e-50f3-9309-6ecd03895d9e`
- `06d801e1-67d3-52b6-a717-29ba68b012b3`
- `096163f6-1dda-5903-81b2-2ad407337a9e`
- `09c9a727-a851-5c5d-965c-d4bd60d38652`
- `0ba24c05-a17a-5bf9-970f-e7d8e709ed9e`
- `0fdb1590-3a8f-5f5e-8438-c74d847b337e`
- `11f6437e-a84a-5584-bd8a-a0de77fd38e9`
- `126ac0de-bb7e-51ca-8579-1dfce4f2988a`
- `1645376b-897e-5e96-968b-3488acf65b6b`
- `23f77ff7-ab6e-5942-a753-63075df41aba`
- `2b261bbe-15e7-5efc-8ce4-0dfa881af278`
- `2c935ecd-b371-55b2-ba8a-1af0a0fc017a`
- `309abf4b-74be-5d2e-bf50-636071ffe99d`
- `32e3ad12-2354-5078-ba55-5862323c8844`
- `3528d58c-35e0-5363-b3b2-1c73d31713ce`
- `3d64dd0a-3efa-5d04-8e5c-699a0f9513cf`
- `46c0b852-91f8-56ae-a721-7610eb6d12e0`
- `47c9cb33-1aef-5e15-8c23-5c7b44ffd0a4`
- `51a1d2e1-58d4-5c91-8241-d7bc37b3ba0d`
- `527be1ca-c15b-5469-8d2b-e3b25bc9883a`
- `52a2dbf0-cd51-5419-94b2-e9856859c755`
- `5f3eabb1-f5a5-53d3-851a-5484cd06f79b`
- `6ec2a350-88e4-5282-8374-efad6de9221c`
- `76e97d4d-0d76-5ae3-b7e9-7e030db65fec`
- `781ab2be-f579-5cef-a1bd-59dae614ee36`
- `8609f4ac-f406-5dbb-8226-c5c08e4a132b`
- `8761e246-116d-55ed-80dd-7a0992125325`
- `89737fe9-9f13-5717-b875-7b6a1d4c72a0`
- `9d8d92d8-fbfe-55f6-89c6-01c87206cdbb`
- `a5ef21b3-c6e1-5b95-bde8-2c9c1bee395d`
- `a6f510b5-ceea-5cbe-98b2-2876be119a7d`
- `a7144486-fc1d-5472-ab96-c36c8362813f`
- `a774a8ac-34ed-5c1e-976f-427f45e7d6a6`
- `aab4538f-2f36-58b7-aca8-0fba17357dde`
- `ab174129-6877-5cc0-ba2f-1e66999bb4ef`
- `af9da515-48a3-5507-95e7-2037012c61b9`
- `ba2c47d1-9fff-59b0-aba8-abadc9447165`
- `c0ad6877-3719-53bc-b1cd-da16178b2fc4`
- `c1ec1966-c446-590f-a3c1-10c152ce62d7`
- `c3ee241b-d418-568b-b476-b6cf390cb2cc`
- `d0beb809-c54d-5d0e-b69a-86c5f40641a0`
- `d7f6fc21-4a31-504b-b50a-685f90a24bda`
- `e3c652b3-b7ae-5e4d-92fa-e1045fcda8e4`
- `e5aff60d-f22f-523d-9930-02ea3bb36452`
- `e8dcdee7-a977-5365-a166-9723ac71423a`
- `eea7639c-f8cb-5dc5-875f-c24e3f31a4dc`
- `f4765165-cd15-59ba-80e1-ac89bc795fa2`
- `f6d1d28c-f55a-5cad-a39b-afbb7b4c2660`
- `f86f7dd4-150d-55b4-a9b0-6577ecf9fe92`
- `f9bcea76-f1a7-57d0-a25d-5662d2d7fe72`

### Distinguishing item IDs (n=49)

- `0a638701-cc04-5b26-9331-990e2cab1c5e`
- `0b089a98-934d-54f2-bfa5-03fdfdb22136`
- `0bbfac30-d61c-5684-b4db-4d2a57ce5b48`
- `1765e6aa-8c53-5085-a042-80af891a67a7`
- `1d7b3ea7-5064-5f02-8054-b9af15749989`
- `219108f3-2c99-55e5-834b-4bc10b2e4046`
- `2365f5ac-e45e-513e-b226-2e16faa5f970`
- `27f34b14-0ea5-5da7-988e-bfadd0e50771`
- `2b034fa8-6e5f-5eb3-8062-4db982238889`
- `37f0f52b-dda5-56fa-8621-799a183e8205`
- `3e554221-77fe-573c-a9f6-d8a59fb7b06e`
- `41139a73-ce8b-59ad-b0b6-102e166fd11b`
- `46a9c1be-53c8-5e5a-aa43-c352b12f3c3c`
- `554d2c4c-23ba-56dc-8258-77809803beff`
- `60168f84-674c-5cfb-a7ff-dac37176b7ea`
- `62a5779f-865c-50b5-b7ee-985a2167cb82`
- `6a48c331-89c5-59b8-88ec-07b47ce8d423`
- `70b1967c-e0b1-59e0-88a9-a476a69eaece`
- `71029a51-e38f-588a-bd3a-68dd0d051b53`
- `740def1a-486e-5058-953c-24d7409ff37f`
- `76c9c317-3510-556d-91c8-335ea1e4f60f`
- `78a198ab-f099-5ab9-b2c7-d5d1314c9f40`
- `79ce6d56-2058-58e7-a493-2f2925a96334`
- `81d7180c-f336-5216-bb3f-939e07b468cc`
- `822876b7-e542-5728-9995-d4bf74e1a096`
- `8458ee46-0f26-5348-9b2f-bfe7a584efa7`
- `87856787-549b-5e1a-b219-632def01bd64`
- `87afff11-0dc0-5c77-8349-04b7d5a6e609`
- `94adb26b-7b59-52d9-99d7-7cc2fea21c3d`
- `aea2524b-a7fa-5050-89de-ef23888b4996`
- `b1936ae1-8dff-568c-b2bb-0286875d16d0`
- `b3a27319-08eb-5c9b-be0a-b016d40f87f4`
- `b6a6ed30-e94e-5c37-a30f-d762f52686b0`
- `bbfe89de-9826-5fd6-adf9-6f76d0399a20`
- `bd95c5db-e77e-5fd8-977b-8180adb51173`
- `bd96f9a5-3622-565b-8f6e-4c4c7c13dcc8`
- `c1c5dc21-c466-56dc-a887-aee7c747c780`
- `c35317c7-d607-5306-a67b-8d1338530236`
- `d56354f9-b63f-50d4-b78b-0100ea31bc35`
- `d58e1207-0b20-55ed-8432-a0cd6dd962a5`
- `d68ea6fe-9c5b-5379-a64d-e90144bf749a`
- `d84c0bbd-7119-5083-98cc-a0ace12c6f00`
- `db0bce37-ea79-54cc-968c-1e3c1d96ef72`
- `e4f3d0e9-34aa-56dd-a2bb-ab4a181afc7d`
- `f4b40464-3bd6-5a51-97d5-39e928007455`
- `f51d7eed-eb7e-5f3e-ac56-4449b75ff36a`
- `fc81f240-8553-5f44-afa1-08abf2b71ad8`
- `ff081637-5a06-5478-96b6-5693d8bd72f2`
- `ff9e96ca-ef84-5f0b-b6ef-9e0f14b06b16`

### Pilot item IDs (lexicographic first 5 equivalence IDs)

- `0027e8d7-4960-5973-8266-d7b17f673831`
- `05f2e4ef-d67e-50f3-9309-6ecd03895d9e`
- `06d801e1-67d3-52b6-a717-29ba68b012b3`
- `096163f6-1dda-5903-81b2-2ad407337a9e`
- `09c9a727-a851-5c5d-965c-d4bd60d38652`

---

## Models

| Role | Provider | Model / snapshot ID |
|---|---|---|
| Snapshot A | Anthropic | `claude-sonnet-4-5-20250929` |
| Snapshot B | OpenAI | `gpt-4.1` |

- Planned collection window: **TBD at pilot start** (placeholder).
- Analyse separately; never pool in a primary significance test.
- Secondary only: difference between the two model-specific paired RDs with an interval.

### Provider caching policy (no live API calls; adapter inspection)

| Provider | Class | Policy |
|---|---|---|
| Anthropic | **A** | Prompt caching opt-in via `cache_control`; confirmatory requests omit it (disabled). |
| OpenAI | **C** | No explicit disable in Chat Completions adapter; cache status not parsed. Record timestamps; run pre-specified timestamp/cache sensitivity. |

Do not change prompt contents merely to defeat caching.

---

## Conditions

All confirmatory cells use `oracle_info=none`, `format_assist=off`, `orchestration_mode=two_phase_no_inject`, `temperature=0.2`, `max_tokens=8192`.

| condition_id | contract | tool_palette | RQ families |
|---|---|---|---|
| bisimulation_T0 | bisimulation | T0_NONE | RQ3 (+ descriptive) |
| bisimulation_T1 | bisimulation | T1_STEP | RQ1, RQ2, RQ3 |
| bisimulation_T3 | bisimulation | T3_VERIFY | RQ3 |
| minimized_dfa_T1 | minimized_dfa | T1_STEP | RQ2 |
| digest_control_T1 | digest_control | T1_STEP | F0a gate |

Exact fingerprints: `docs/clean_v2/manifests/manifest_*.json` → `condition_catalog`.

---

## Execution

| Parameter | Frozen value |
|---|---|
| k | **5** (not adaptive) |
| temperature | 0.2 |
| max_tokens | 8192 (hitting cap = EXPERIMENTAL OUTCOME) |
| top_p | null (provider default / unspecified) |
| execution_order_seed | **20260902** |
| execution policy | full Cartesian task list shuffled; interleaved across item×model×condition×rep |
| max_verifier_calls | **3** |
| max_reruns | **3** (infrastructure only; same repetition index) |
| min_valid_generations_per_condition | **2** |
| item exclusion tipping fraction | 0.10 |

Scheduler: `fsmreasonbench.clean_v2.confirmatory.scheduler`.  
Master schedule: `docs/clean_v2/manifests/manifest_confirmatory_master.json` (n=3040 tasks).

Each task stores: planned_position, execution_order_seed, actual_start_timestamp, actual_completion_timestamp, provider_request_id, cache_status.

---

## Outcomes

| Outcome | Role |
|---|---|
| **witness_valid** | **Primary** |
| **witness_valid_first** | **Co-primary diagnostic for T1→T3 only** (silent first complete proposal) |
| fully_correct, extractable, verdict_correct, first_failure | Secondary / descriptive |
| verifier_call_count, verifier_call_cap_reached, coarse responses | T3 process diagnostics |

`witness_valid_first`: whether the first complete model-generated witness proposal would be accepted by the verifier, evaluated silently without revealing this evaluator-only result through any additional channel that alters model context or tool state. (Coarse T3 feedback on executed verifier calls remains as designed; the silent metric computation itself must not mutate messages/tool outputs.)

Interpretation for T1→T3:

- Improvement on both first and final → evidence for improved witness production under verifier access.
- Improvement only on final → evidence for verifier-guided search, not improved first-attempt construction.

---

## Experimental unit

| Concept | Definition |
|---|---|
| Observation | item × model × condition × repetition generation |
| Treatment cell | item × model × condition |
| Pairing / blocking unit | item, within model |
| Inferentially independent unit | item, within model |
| Effective inferential n (RQ2/RQ3) | 51 items per model (not 255 generations) |
| Model | fixed factor (two snapshots) |

---

## Analysis

### Stage 1

For item i and condition c:  
`p_hat(i,c) = (# valid outcome successes) / (# valid attempted generations in cell)`.

### Primary estimand

`D_i = p_hat(i, A) − p_hat(i, B)`; report `mean(D_i)` as percentage-point paired risk difference.

### Interval

95% BCa bootstrap over **items**, 10,000 resamples, seed `424242`. All conditions/reps of an item move together.

### Exact/associated test

Within-item sign-flip permutation on `D_i`, two-sided, statistic `mean(D_i)`, 10,000 draws (or exact if cheaper), seed `1357911`.

**Do not** use pooled McNemar over generations.

### Boundary fallback

If BCa is degenerate (constant paired differences / boundary), use Newcombe–Wilson paired risk-difference interval as the pre-specified boundary-safe alternative. Tango score is not used (no reliable in-repo implementation; avoided new uncertain custom stats dependency).

### Incomplete cells

Retain item in an analysis family only if every condition in that family has ≥2 valid generations. Equal item weights. Report excluded IDs. If >10% excluded: tipping-point sensitivity; if extreme assumptions flip sign → `INCONCLUSIVE DUE TO MISSINGNESS`.

### Ceiling/floor

Primary analysis remains valid at 0/1. If both sides floor-zero on every item: `CONTRAST NOT ESTIMABLE AT THIS CAPABILITY LEVEL` (not "no effect"). Conditional metrics with denominator <10: raw counts only.

### Sensitivity analyses (implemented before real data)

1. Majority-vote per item + discordant-pair counts  
2. Boundary-safe Newcombe–Wilson RD interval  
3. Complete-k-only analysis (config hook)  
4. Infrastructure missingness tipping-point  
5. Provider-time drift / cache diagnostic (secondary)  
6. Safety-refusal-excluded sensitivity  
7. Optional penalized logistic via trusted library only if added later under new spec version  

None replaces the primary analysis after unblinding.

Implementation: `fsmreasonbench.clean_v2.confirmatory.analysis`.

---

## Multiplicity

Within **each model** separately, one confirmatory family of three contrasts (RQ2; RQ3 T0–T1; RQ3 T1–T3). Holm–Bonferroni FWER = 0.05.

- Do **not** adjust across models (separate replication scopes).
- Confidence intervals remain **nominal 95%**.
- Holm applies to inferential decisions / p-values, **not** to the nominal intervals.
- T1→T3 stronger construction interpretation: intersection of final and first outcomes associated with one RQ3 contrast.

---

## Missingness classification (generation time; machine-readable)

### INFRASTRUCTURE (rerun same repetition index; does **not** enter `n_attempted`; max_reruns=3)

HTTP/API timeout; rate limit/quota; transport/network failure; provider 5xx; provider stream abort; harness internal exception; verifier/tool crash caused by harness.

### EXPERIMENTAL OUTCOME (enters `n_attempted`; **no** rerun)

Malformed model output; invalid model tool call; model-caused tool validation error; completion reaching max_tokens; safety refusal; empty completion with normal stop; parser failure.

Safety refusals: count as non-extractable in primary; report refusal count separately; pre-specify sensitivity excluding refusals.

Classifier: `fsmreasonbench.clean_v2.confirmatory.missingness.classify_generation_attempt`.  
**No post-hoc manual recategorization.**

---

## Pilot (configuration only; not executed in this freeze)

- 5 items: lexicographic first 5 equivalence IDs (within-eq structure constant).
- Both models; cells: bisimulation/T1, minimized_dfa/T1, bisimulation/T0, bisimulation/T3, plus digest_control; k=2.
- Pilot generations excluded from confirmatory analysis; pilot items remain in confirmatory cohort.
- Report guard: `fsmreasonbench.clean_v2.confirmatory.pilot_guard` forbids condition-wise witness-valid rates, model-wise effects, RQ contrasts, p-values.
- Allowed: artifact completeness, schema health, extraction mechanics, tokens, latency, cost, infrastructure errors, verifier call counts, at-least-one-valid-witness feasibility bit per feasible contract.

**Do not run the pilot during this freeze task.**

---

## Falsification / decision rules

### Validity gates

- **F0a:** digest_control `witness_valid` > 0 → campaign/pipeline invalid until explained.
- **F0b:** any deterministic sentinel/fingerprint failure → affected campaign invalid.
- **F0c:** RQ2 `|delta_verdict| > 10` pp and interval excludes 0 → withdraw clean witness-only RQ2 interpretation.
- **F0d:** differential infrastructure loss >5 pp between contrasted conditions → mandatory tipping-point; sign flip → `INCONCLUSIVE DUE TO MISSINGNESS`.

### RQ2

- Strong replicated: |mean paired RD| ≥ 15 pp; Holm met; same direction both snapshots.
- Snapshot-specific: criteria met for one snapshot only.
- No meaningful large effect detected: both snapshots `|RD| < 10` pp and intervals compatible with no effect larger than ~20 pp (cautious wording; **do not** write "no effect").
- Intermediate: `INCONCLUSIVE` allowed.
- Both contracts floor-zero: `NOT ESTIMABLE AT THIS CAPABILITY LEVEL`.

### RQ3 T0→T1

Strong evidence: RD ≥ 10 pp; Holm met; same sign across snapshots.

### RQ3 T1→T3

- Stronger construction: ≥10 pp on final **and** ≥10 pp on first; inferential criterion; same sign both snapshots.
- Search-only: final improves materially; first does not.
- If effects almost exclusive to generations exhausting all three verifier calls: flag attempt-budget dependence.

---

## Confirmatory hierarchy

| Tier | Content |
|---|---|
| 0 | Validity gates F0a–F0d |
| 1 | RQ2 / RQ3 primary contrasts |
| 2 | RQ1 descriptive |
| 3 | Secondary estimation |
| 4 | Exploratory (pre-treatment predictors only) |

---

## Contract burden

Record descriptively. **Do not** put certificate size / field counts / relation-pair counts / witness state or transition counts / sequence length into the primary statistical model. Exploratory predictors: pre-treatment input properties only (machine size, alphabet size, product-state size).

---

## AI assistance

Harness and confirmatory analysis/pre-spec implementation were produced with Cursor AI assistance under human direction (2026-09-02). See `docs/clean_v2/AI_ASSISTED_PROVENANCE.md`. Historical `Co-authored-by: Cursor` commits on scientific paths remain disclosed and unrewritten.

---

## Change control

Any modification after the first confirmatory generation invalidates the frozen campaign unless it is purely downstream presentation.

Changes affecting prompts, contracts, tools, scoring, verifier, parser, retries, model parameters, item set, or statistical plan require a **new** pre-spec version and a **new** campaign.

---

## Manifest index

See `docs/clean_v2/manifests/INDEX.json`.

| Manifest | n_tasks |
|---|---|
| RQ1 | 1000 |
| RQ2 | 1020 |
| RQ3 | 1530 |
| DIGEST | 510 |
| PILOT | 100 |
| CONFIRMATORY_MASTER | 3040 |
