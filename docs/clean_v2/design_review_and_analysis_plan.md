# Hostile Design Review and Frozen Analysis Plan
**Role:** senior statistical reviewer / ESE methodologist / adversarial TOSEM–TSE reviewer
**Object of review:** planned confirmatory campaign on the clean harness (RQ1–RQ3), pre-data
**Stance:** conservative. Every recommendation below is chosen so that the plan still reads as competent if all effects are null.

---

## A. Statistical diagnosis

Issues are numbered for cross-reference. Severity: **Fatal** = the intended inference cannot be drawn at all; **Major** = inference survives only with a materially narrower claim or a design change; **Moderate** = fixable in analysis or pre-specification; **Minor** = reporting hygiene.

### A1. The T3 treatment supplies the primary outcome signal — **Major, borderline Fatal**
`witness_valid` is defined as acceptance by the verifier. T3_VERIFY gives the model access to that verifier. Even coarse, non-constructive accept/reject feedback is a *membership oracle over the outcome space*. With an unbounded or unlogged call budget, a model can search until accepted, and the T1→T3 contrast degenerates into "how many times may the model resubmit", which is not a claim about tool support.

This is the single most exploitable weakness in the plan. A TOSEM reviewer needs one sentence to write it.

*Requires:* design instrumentation + narrower claims. Hard cap on verifier calls (pre-specified integer, recommended `max_verifier_calls = 3`), the call count logged per generation, and a **co-reported first-proposal outcome** `witness_valid_first` (validity of the model's *initial* witness, evaluated by the verifier but never revealed). The confirmatory claim must be worded as the effect of *access to bounded non-constructive acceptance feedback within a fixed retry budget*, not "tool support improves witness construction".

### A2. Condition confounded with wall-clock execution order and provider drift — **Major**
Pinned snapshots pin weights, not the serving stack (routing, quantization, speculative decoding, safety filters, caching). If the campaign is executed condition-by-condition, any provider-side change during the run is perfectly aliased with the treatment. The previous submission's single-pass design had the same exposure.

*Requires:* redesign of the execution schedule (cheap, no harness change). Generate the full task list of (item × model × condition × repetition), shuffle it under a recorded seed, and execute in that interleaved order. Record a timestamp per generation. Disable provider prompt caching, or record cache-hit status and pre-specify it as a covariate in a sensitivity analysis. Pre-specify a drift diagnostic: outcome rate vs. timestamp decile, reported.

### A3. Only equivalence items in RQ2/RQ3 makes `verdict_correct` uninterpretable — **Major**
On a universe of 51 items that are *all* equivalent, a model with pure yes-bias scores 51/51 on verdict. `verdict_correct` therefore carries no information about discrimination, and every conditional metric that divides by it (`P(witness_valid | verdict_correct)`) has a denominator inflated by lucky guesses. The previous "verdict–witness gap" framing died partly of this; re-importing the same denominator through the back door would be worse the second time.

*Requires:* narrower claims + reanalysis structure. (i) No verdict-accuracy claim may be made from the 51-item universe. (ii) Verdict accuracy is estimated only on the combined 100-item RQ1 universe, where the 49 distinguishing items identify response bias; report per model a bias index (e.g. proportion answering "equivalent" on distinguishing items). (iii) `P(witness_valid | verdict_correct)` is demoted to descriptive with the denominator printed, and is explicitly flagged as conditioning on a post-treatment variable (see A7).

### A4. Pseudoreplication risk from repetitions — **Major (avoided if §B is followed)**
Treating 51 × 3 = 153 generations as independent items inflates precision by roughly √(1 + (k−1)ρ). With binary outcomes at T = 0.2, within-cell ρ is likely 0.7–0.95, so the inflation is close to √3 ≈ 1.7×. Any pooled McNemar over 153 pairs is invalid.

*Requires:* reanalysis only — fix the unit at the item (§B).

### A5. Two models cannot be a random effect, and cannot support generalization — **Major (handled by scope wording)**
A variance component estimated from two levels is not identifiable in any useful sense. Model must be fixed, and no statement about "LLMs" is licensed. Exact permissible scope in §F.

### A6. 51 items is a hard ceiling on detectable effects — **Major**
Under paired binary analysis, nothing is detectable at α = 0.05 unless at least 6 items discord, and the design has ≥80% power only for absolute differences of roughly 15–20 percentage points under plausible discordance (§N). A null result therefore cannot be reported as "no effect"; it can only be reported as "no effect larger than ~20 pp detected". Pre-specifying this now is the difference between an honest paper and a rejected one.

*Requires:* narrower claims for RQ3, and pre-specification of "inconclusive" as a legitimate reported outcome.

### A7. Conditional outcomes condition on a post-treatment variable — **Moderate**
`P(witness_valid | extractable)` and `P(witness_valid | verdict_correct)` condition on variables the treatment may itself affect. Comparing these across conditions is a collider-stratification comparison, not a causal contrast. They may be reported, never tested confirmatorily.

*Requires:* reanalysis only — demote to descriptive, print denominators, add the caveat in the pre-spec, not just in the paper.

### A8. Four "primary outcomes" is not a primary outcome — **Moderate**
`extractable`, `verdict_correct`, `witness_valid`, `fully_correct` are all listed as primary. That is four families of tests and unbounded post-hoc emphasis. Choose one: `witness_valid`.

*Requires:* reanalysis only (§P).

### A9. First-failure categories are compositional, not four independent outcomes — **Moderate**
The four first-failure cells sum to 1 within item, so separate binomial tests are both multiple and negatively dependent. Report as a composition with simultaneous intervals; do not test cell-by-cell.

### A10. Ceiling and floor cells break logistic models — **Moderate**
0/51 or 51/51 produces complete separation; `glmer` will return an infinite coefficient or a boundary singular fit, and any reviewer running the code will see it. Handled by choosing a boundary-safe primary method (§D, §M).

### A11. Contract-burden metadata is post-treatment — **Moderate**
State count, transition count, serialized size, field count, relation-pair count and sequence length of the *required witness* are realizations of the treatment. Adjusting for them removes exactly the mechanism under study (§L).

### A12. Item provenance carries over from the rejected study — **Moderate, conditionally Major**
The 51 are the equivalence stratum of the previous 100-item cohort. Stratifying by a pre-treatment property (equivalence) is legitimate. What is not legitimate, and must be audited, is any historical removal of items on the basis of observed model performance. If such filtering occurred, the cohort is outcome-selected and the item random effect no longer generalizes (§K).

### A13. T3 changes inference-time compute, not only information — **Moderate**
Even with a capped call budget, T3 permits more total generation and more attempts than T1. The effect of "information" and "extra attempts" are not separable in this design. Claim scope must say *palette*, not *information*.

### A14. Model × condition interaction is under-powered by construction — **Moderate**
An interaction test on 51 paired items with two models has roughly a quarter of the power of the main effect. It must be secondary and framed as estimation, never as "no interaction was found".

### A15. Missing/failed generations can select on difficulty — **Moderate**
Timeouts and truncations correlate with long, hard items. Dropping them silently biases toward easy items and inflates all rates. Deterministic rule in §I.

### A16. `k = 3` gives near-zero resolution on run-to-run instability — **Minor for the contrast, Major for the stated instability goal**
The plan says instability is an explicit target. With k = 3 and per-item flip probability p, the chance of *observing* any disagreement is 1 − p³ − (1−p)³ — that is 0.27 at p = 0.10 and 0.14 at p = 0.05. k = 3 will therefore report most unstable items as stable. If instability is a finding, k = 3 does not support it (§C).

### A17. Digest control is a pipeline validity test, not a footnote — **Minor**
It should be promoted to a pre-specified falsifier of the entire run (§O), not reported as a secondary curiosity.

### A18. Analyst degrees of freedom after unblinding — **Minor**
Nothing in the plan prevents the analysis code from being written after the numbers are visible.

*Requires:* pre-specification. Write and unit-test the full analysis pipeline against simulated data and against label-permuted real data before unblinding; commit it with a tag prior to first confirmatory generation.

---

## B. Experimental unit and dependence structure

Stated precisely, because this is where the previous submission was attackable.

| Level | Role |
|---|---|
| **Generation** (item × model × condition × repetition) | Unit of *observation*. Carries decoding stochasticity only. Not independent. |
| **Cell** (item × model × condition) | Unit of *treatment assignment*. All conditions are applied within item, so assignment is a within-item, fully-crossed, non-randomized allocation. |
| **Item** (within model) | Unit of *pairing/blocking* and unit of **inferential independence**. Effective n = 51 per model for RQ2/RQ3. |
| **Model** | Fixed, 2 levels. Not a sampling unit, not a source of generalization. |

**Sources of random variation.** Two, and only two are estimable: (i) between-item heterogeneity, which will dominate — expect a high intra-item correlation across repetitions; (ii) within-cell generation noise, small at T = 0.2. Item difficulty is shared across conditions, which is precisely why the paired/within-item analysis is the correct one: shared difficulty is *blocked out*, not a nuisance.

**Consequence.** Repetitions are pseudoreplicates *for the condition contrast*. They are legitimate data for estimating within-cell noise and for reducing measurement error in the per-item estimate, but they must never enter the degrees of freedom of the treatment comparison. The analysis therefore proceeds in two stages: collapse repetitions to a per-item, per-condition proportion; perform inference across items.

**No pooling across models in a primary test.** Pooling forces either a shared item effect across models (false) or a crossed structure with 2 fixed levels and an interaction the design cannot resolve (A14).

---

## C. Recommended k

### What each k buys

For the **primary contrast**, the variance of the mean paired difference is approximately σ²_between/n + 2σ²_within/(nk). Because σ²_between dominates for heterogeneous formal-reasoning items, k has a small and rapidly saturating effect on the precision of the treatment estimate. Moving k = 1 → 3 removes most of the recoverable within-cell noise; 3 → 5 recovers little; 5 → 10 recovers almost nothing at T = 0.2.

For the **instability outcome**, the arithmetic is different and unfavourable to k = 3, as in A16.

For **graded per-item differences**, k determines the granularity of the per-item difference: k = 3 gives differences in {−1, −⅔, −⅓, 0, ⅓, ⅔, 1}, k = 5 gives fifths. Graded differences are what make the permutation test in §D more powerful than a dichotomized McNemar, and finer granularity helps modestly.

| k | Estimates the treatment contrast | Estimates per-item flip probability | Majority vote | Marginal cost |
|---|---|---|---|---|
| 1 | Adequate but confounds decoding noise with item effect; no instability data at all | No | Undefined | 1× |
| 3 | Adequate; ~2/3 of recoverable noise removed | Poorly — misses ~73% of items with p_flip = 0.10 | Well-defined, but 2–1 majorities are fragile | 3× |
| 5 | Marginally better than 3 | Usable at the cohort level; detects p_flip = 0.10 with prob. 0.41 | Well-defined, 3–2 and 4–1 distinguishable | 5× |
| 10 | Indistinguishable from 5 for the contrast | Good per-item resolution | Robust | 10× |

### Recommendation

**Increase to k = 5, conditional on budget; k = 3 is defensible only if the instability claim is demoted to descriptive.**

Cost check: the confirmatory design has 4 unique cells per item per model (bisimulation×T1, minimized_dfa×T1, bisimulation×T0, bisimulation×T3), so 51 × 2 × 4 = 408 cells; k = 3 → 1,224 generations, k = 5 → 2,040. Adding the digest control and the RQ1 distinguishing items keeps the total under ~3,500 generations at k = 5. This is not a budget-limiting quantity for two API models. Take k = 5.

**Do not use adaptive repetition.** Outcome-dependent stopping on binary outcomes is exactly the researcher degree of freedom the whole exercise is designed to remove, and no stopping rule based on observed disagreement is neutral: stopping early on unanimous cells and continuing on split cells biases the estimated instability upward and the per-item proportion toward 0.5. If cost genuinely binds, prefer a fixed k = 3 for all cells over an adaptive schedule.

---

## D. Primary analysis — RQ2

### Method comparison

| Method | Strengths here | Weaknesses here |
|---|---|---|
| McNemar per repetition | Simple, exact | Three tests, arbitrary combination rule, discards within-item information, invites selective reporting |
| Pooled McNemar over 153 pairs | Simple | Invalid — pseudoreplication (A4); a reviewer will reject on this alone |
| GLMM, logit, `(1\|item)` | Uses all data, standard | Separation at ceiling/floor (A10); 51 clusters is thin for variance-component estimation; conditional (subject-specific) coefficients are awkward to interpret as risk differences; convergence/singular-fit noise |
| GEE, exchangeable, cluster = item | Marginal estimates, robust SE, risk-difference link possible | 51 clusters is at the lower edge for robust SEs; needs Mancl–DeRouen or Fay–Graubard small-sample correction; identity-link convergence failures at boundaries |
| Permutation / randomization on per-item differences | Exact under the sharp null, assumption-free, boundary-safe, handles graded differences, matches the pairing exactly | No model, no covariate adjustment, tests a sharp null |
| Hierarchical Bayesian logistic | Handles separation via priors, gives credible intervals, no dichotomous decisions | Prior sensitivity becomes an argument surface with a hostile reviewer; heavier to defend for a 2-condition paired contrast |
| Majority aggregation + exact McNemar | Transparent, boundary-safe | Discards graded information; 2–1 majorities create misclassification; strictly less powerful |

### Chosen primary analysis

**Estimation-first, with a single exact test attached. No single p-value is the headline; the headline is the interval.**

- **Stage 1 (collapse).** For item *i*, model *m*, condition *c*, compute p̂ᵢₘc = (number of valid witnesses) / (number of *valid attempted* generations in that cell).
- **Response variable.** Dᵢₘ = p̂ᵢₘ,bisimulation − p̂ᵢₘ,minimized_dfa, one value per item per model.
- **Primary estimand.** Δ̂ₘ = mean over items of Dᵢₘ — the mean paired risk difference in witness validity, on the probability scale, in percentage points.
- **Uncertainty.** BCa bootstrap over items (10,000 resamples, seed pre-registered), stratified by nothing, resampling whole items so that all conditions and repetitions for an item move together. Report the 95% interval.
- **Test.** Within-item sign-flip permutation on Dᵢₘ (Monte Carlo, 10,000 draws, same seed family), two-sided, statistic = mean(D). Items with Dᵢₘ = 0 contribute nothing and require no special handling.
- **Fixed effects:** contract (2 levels). **Random effects:** none — the item effect is removed by differencing, which is the exact-inference equivalent of an item random intercept with no distributional assumption.
- **Pairing:** by item ID within model. **Repetitions:** averaged within cell (Stage 1); they never enter the degrees of freedom.
- **Model:** analysed separately per snapshot (§F). Two parallel primary analyses, not a pooled one. **Interaction** is a secondary estimand: Δ̂_Sonnet − Δ̂_GPT-4.1 with a bootstrap interval, reported, not tested confirmatorily.
- **Pre-specified sensitivity analyses (all reported regardless of outcome):** (i) majority-vote dichotomization + exact McNemar with a Tango score interval for the paired risk difference; (ii) GLMM `witness_valid ~ contract + (1|item)` with Firth-type penalization or a weakly-informative prior, per model, at generation level; (iii) analysis restricted to items with complete k in both conditions.

Rationale for choosing this over the GLMM: it is exact, immune to separation, immune to convergence artefacts, has a single interpretable number in percentage points, and its assumptions can be stated in one sentence to a reviewer. The GLMM is retained as a sensitivity analysis so that a reviewer who prefers it sees it, but it is not load-bearing.

### Mandatory negative control for RQ2

The witness contract should not affect *verdict* determination if the pipeline is orthogonal. Pre-specify: estimate the same paired difference for `verdict_correct` between the two contracts. A materially non-zero difference indicates the contract is leaking into the verdict path and **invalidates the RQ2 causal reading**. (Given A3, this is a pipeline diagnostic only, not a verdict-accuracy claim.)

---

## E. Primary analysis — RQ3

**Do not impose ordinality.** T0 → T1 adds a non-answer-producing stepping tool; T1 → T3 adds bounded acceptance feedback. These are qualitatively different manipulations. A linear trend test across T0 < T1 < T3 would be an assumption smuggled in as a coding choice.

**Contrast structure:**

- **Primary:** T0 vs T1, and T1 vs T3. Two adjacent, mechanistically distinct contrasts.
- **Secondary:** T0 vs T3 (a composite of the two primaries; it adds no independent information and is reported for completeness).
- **No omnibus gate.** A global 3-level test before two pre-specified contrasts adds a stage, costs power, and answers no question anyone asked. With exactly two pre-specified primary contrasts, go straight to them under the multiplicity scheme in §H.

**Framework:** identical to §D — Stage-1 collapse to per-item proportions, per-item differences, mean paired risk difference with BCa bootstrap interval, sign-flip permutation test, per model, contract fixed at `bisimulation`.

**Two additions specific to T3 (from A1 and A13):**

1. **Co-primary outcome for T1 vs T3:** the contrast is estimated twice — once on `witness_valid` (final submitted witness) and once on `witness_valid_first` (the model's first proposal, evaluated silently). The confirmatory claim about *non-answer-producing support improving witness construction* is supported only if the effect survives on `witness_valid_first`. If the effect appears only on `witness_valid`, the correct conclusion is that bounded acceptance feedback enables **search**, not improved construction — a different and weaker claim that must be pre-committed now, not chosen later.
2. **Reported alongside, always:** distribution of verifier-call counts per generation, and the proportion of T3 generations that hit the cap.

---

## F. Model handling

**Choice: A, with a structured cross-model reporting rule.** Analyse each snapshot separately; treat agreement across snapshots as conceptual replication, not as statistical pooling.

- **B (pooled, model fixed + interaction)** would be defensible for estimation but buys nothing: with two levels the "pooled" main effect is just a weighted average of two estimates already reported, and the interaction is under-powered (A14). It also forces a shared item random effect across models, which is not credible.
- **C (model random)** is not estimable with two levels. Reject.
- **D:** the only worthwhile variant of D is to *report* the between-model difference as an estimand with an interval, which is included as a secondary in §D.

**Permissible inferential target — exact wording to freeze:**

> The inferential scope is limited to the two pinned model snapshots evaluated (Claude Sonnet 4.5, snapshot ID `<id>`; GPT-4.1, snapshot ID `<id>`), as served by their respective providers during the collection window `<start>`–`<end>`, on the population of equivalence items generated by generator `<G>` under parameters `<P>` and seed `<s>`, under the fixed prompt skeleton, decoding configuration, parser, verifier, orchestration and retry policy recorded in experiment fingerprint `<hash>`. No inference is drawn about language models in general, about other snapshots of the same model families, about non-equivalence items, or about other witness contracts, tool palettes or prompt formulations.

**Cross-model claim rule (pre-specify):** a finding is described as *replicated* only if the point estimates agree in sign and both intervals exclude the null-region boundary in the same direction. A finding present in one snapshot only is reported as snapshot-specific, in those words, in the abstract.

---

## G. Effect sizes

**Primary: the paired (mean within-item) risk difference in percentage points, with a 95% BCa bootstrap interval.** Absolute differences dominate throughout.

Reasons: empirical SE readers reason in "how many of the 51 items changed"; the outcome rates will plausibly sit near boundaries where odds ratios explode or are undefined; and a risk difference is stable and interpretable at 0/51 and 51/51 where a matched odds ratio is not.

**Reported alongside, for every primary contrast:**

- The discordant-pair counts (b, c) on the majority-vote dichotomization, plus the discordant-pair proportion (b + c)/n. This is the transparency number: it tells a reviewer immediately whether the comparison had any information in it at all (§N).
- The marginal rates per condition with Wilson intervals, clustered by item via the same bootstrap.
- The paired risk difference from the majority-vote dichotomization with a **Tango score interval**, which is boundary-safe and is the standard the biostatistics-literate reviewer will look for.

**Secondary:** matched odds ratio (McNemar / conditional), reported only when both discordant cells are non-zero, explicitly labelled as a relative measure and never used as the headline.

**Not used:** number-needed-to-change style metrics. They are unfamiliar in this literature and invite a reciprocal-of-a-small-number instability problem.

---

## H. Multiplicity

**All planned confirmatory contrasts:**

| # | RQ | Contrast | Outcome | Model |
|---|---|---|---|---|
| 1 | RQ2 | bisimulation vs minimized_dfa | witness_valid | Sonnet 4.5 |
| 2 | RQ3 | T0 vs T1 | witness_valid | Sonnet 4.5 |
| 3 | RQ3 | T1 vs T3 | witness_valid **and** witness_valid_first (co-primary, both must hold) | Sonnet 4.5 |
| 4 | RQ2 | bisimulation vs minimized_dfa | witness_valid | GPT-4.1 |
| 5 | RQ3 | T0 vs T1 | witness_valid | GPT-4.1 |
| 6 | RQ3 | T1 vs T3 | witness_valid **and** witness_valid_first (co-primary) | GPT-4.1 |

RQ1 contributes **no** confirmatory contrast — it is descriptive by construction (§P).

**Recommendation: Holm–Bonferroni within each model, over that model's three contrasts (FWER = 0.05 per snapshot). No adjustment across models.**

Justification. The two snapshots are separate scientific replicates with separate inferential scopes (§F); each is reported as its own experiment, so error control belongs within each. Adjusting across all six would drive the smallest α to 0.0083 and, given the power arithmetic in §N, would make the design incapable of detecting anything but very large effects — over-correction into uselessness. Conversely, the three contrasts *within* a model are a genuine family: they share an outcome, a cohort and a narrative, and leaving them uncorrected is p-value fishing.

Considered and rejected:
- **Intersection–union across models** (requiring significance in both, which needs no adjustment) is scientifically attractive but multiplies the power loss: at ~0.65 power per model, joint power falls to ~0.4. The replication requirement is retained as a *reporting* rule in §F, decoupled from error control, which achieves the scientific goal without the statistical cost.
- **Benjamini–Hochberg** is a screening procedure. Six pre-specified confirmatory contrasts are not a screen.
- **No adjustment** is indefensible with three contrasts on one outcome in one cohort.

**Interval reporting:** confidence intervals are reported at nominal 95% and are *not* Holm-adjusted; the pre-spec must state that intervals are nominal and that only the p-value decisions carry FWER control. Do not silently mix the two.

**Co-primary rule for contrast 3/6:** both `witness_valid` and `witness_valid_first` must clear the Holm-adjusted threshold in the same direction. Because this is an intersection requirement, it consumes one Holm slot, not two.

---

## I. Missingness and rerun policy

The rule must be a **deterministic function of machine-readable fields** (`finish_reason`, HTTP status, exception class, parser return code) fixed before any data is seen. Ambiguity here is what sank the previous submission.

### Classification table (freeze verbatim)

| Event | Detection field | Class | Disposition |
|---|---|---|---|
| API timeout | transport exception / HTTP 408, 504 | INFRASTRUCTURE | Rerun same repetition index |
| Rate limit / quota | HTTP 429, 402 | INFRASTRUCTURE | Rerun same repetition index (after backoff) |
| Transport/network error | connection exception | INFRASTRUCTURE | Rerun same repetition index |
| Provider 5xx | HTTP 5xx | INFRASTRUCTURE | Rerun same repetition index |
| Harness internal exception | traceback origin in harness module | INFRASTRUCTURE | Rerun after fix; if the fix changes the fingerprint, the whole campaign restarts |
| Tool execution failure, cause = harness/verifier crash | exception origin in tool module | INFRASTRUCTURE | Rerun same repetition index |
| Tool execution failure, cause = malformed model tool call | tool returns validation error | **OUTCOME** | Counted; first-failure = extraction |
| Truncation at the pre-specified `max_tokens` cap | `finish_reason == "length"` | **OUTCOME** | Counted; first-failure = extraction |
| Truncation from provider-side stream abort | stream error, `finish_reason` absent/null | INFRASTRUCTURE | Rerun same repetition index |
| Malformed / unparseable response | parser return code | **OUTCOME** | Counted; first-failure = extraction |
| Safety refusal | refusal flag or pre-registered refusal regex on a non-parsing response | **OUTCOME** | Counted as non-extractable in primary; refusal count reported separately; sensitivity analysis excluding refusals is pre-specified |
| Empty completion | zero-length content, `finish_reason == "stop"` | **OUTCOME** | Counted; first-failure = extraction |

**Invariants:**

- INFRASTRUCTURE events **never** enter numerator or denominator. They are logged with full error payloads and reported as an infrastructure-loss count per condition.
- OUTCOME events **always** enter `n_attempted`. There is no category of "model did badly, so we excluded it".
- Every classification decision is written to the run artefact at generation time by the harness, not assigned later by a human.
- The `max_tokens` cap is a *pre-specified* design parameter; changing it after the pilot changes the fingerprint (§J).

**Balance diagnostic:** report infrastructure-loss counts by condition. Differential infrastructure loss across conditions (e.g. T3 timing out more because it generates more) is itself a threat; pre-specify that if the loss rate differs by more than 5 percentage points between any two conditions being contrasted, the contrast is reported with an explicit caveat and a worst-case sensitivity analysis (§I, tipping point).

---

## J. Repetition failure policy

**Policy: rerun the same repetition index, up to `max_reruns = 3` attempts, logging every attempt.**

Repetition indices are labels, not scientific units, and preserving the index keeps the cell shape identical across conditions, which preserves pairing trivially. Creating a new index is equivalent but adds bookkeeping and invites the appearance of selective regeneration; leaving it missing throws away recoverable data.

**If a cell still has fewer than k valid generations after reruns:**

1. Do **not** drop the item on that basis alone. The primary estimand is a per-item proportion, which is well-defined over the available generations, and items are weighted **equally** — not by their number of valid generations — so unequal k does not distort the pairing.
2. **Item retention rule:** an item is retained for a given model and RQ family if and only if it has **≥ 2 valid generations in every condition** of that family for that model. Otherwise it is excluded from that family for that model, and pairing is preserved by construction (the item is absent from both sides).
3. Report the exclusion count and the item IDs excluded, per model per family.
4. **Escalation:** if more than 10% of items are excluded in any family, the primary analysis is reported with a mandatory sensitivity analysis over the full 51: a **tipping-point analysis** setting all missing cells first to valid and then to invalid, reporting how the estimate moves. If the sign of the primary estimate flips under either extreme, the contrast is reported as **inconclusive** regardless of its p-value.

---

## K. Pilot policy

Your default — pilot outputs excluded from confirmatory analysis — is correct, and I will not argue against it. Excluding a handful of pilot generations costs nothing, and including them would mix fingerprints if anything is fixed after the pilot. But one refinement matters:

**Pilot *items* remain in the confirmatory cohort. Only pilot *generations* are discarded.** Removing the pilot items would shrink n from 51 to 46 and, worse, would remove items selected by a process that touched the data.

### Specification

- **Items:** 5, selected deterministically as the first 5 item IDs under a pre-registered lexicographic sort of the ID string. No judgement, no "representative" hand-picking.
- **Models:** both snapshots.
- **Conditions:** all four confirmatory cells plus `digest_control`, so every code path and both feasible contracts are exercised.
- **Repetitions:** k = 2. Enough to exercise the repetition and rerun machinery; too few to characterize anything scientific.
- **Blinding.** The pilot report is restricted to mechanical health indicators, and the pipeline must physically refuse to emit condition-wise outcome rates. Permitted: artefact completeness, schema validity, extraction rate (aggregate, not by condition), token/latency/cost, error-class histogram, non-degeneracy check (submissions differ across items), verifier-call counts, sentinel-test results, `digest_control` = 0. Permitted as a single bit per contract: "at least one valid witness was produced under this contract" — feasibility only, no rate.
- **Prohibited:** any condition-wise or model-wise `witness_valid` rate.

**May change after the pilot** (each change increments the pre-spec version and produces a new experiment fingerprint; all pilot data is discarded and the pilot may be re-run): harness bugs; timeout, backoff and rerun parameters; `max_tokens` cap if the observed truncation rate makes the cap a binding artefact rather than a measurement; logging and artefact schema; provider client configuration; cost/scheduling parameters; the execution shuffle seed.

**May not change under any circumstance:** the RQs; the item set; the conditions and their definitions; the witness contracts; the prompt skeleton (beyond typographical corrections, which must be diffed in the commit); temperature; k; the primary outcome; the primary contrasts; the analysis method; the multiplicity scheme; the falsification thresholds; the inferential hierarchy.

**Hard rule to write down:** if the pilot reveals a problem whose fix requires touching anything in the "may not change" list, the pre-specification is versioned, the change is documented with its motivation *before* any confirmatory data exists, and the pilot is re-run from scratch. That is legitimate. Discovering the same problem after confirmatory data exists is not fixable, and the campaign restarts.

---

## L. Item-set decision

**Decision: reuse all 51, conditional on a provenance audit; do not subset, do not regenerate by default.**

Subsetting or randomly sampling from the 51 adds a researcher degree of freedom and reduces power for no gain. Regenerating a fresh cohort is only warranted if the audit fails.

**Audit — answer each in writing in the pre-spec, before collection:**

1. **Generator provenance.** Which generator, which parameters, which seed produced the original 100? Is the generation script committed and reproducible?
2. **Outcome-dependent filtering.** Was any item ever removed, replaced or regenerated on the basis of observed model performance in the previous study? This is the decisive question.
3. **Difficulty restriction.** Distribution of pre-treatment structural properties (input automaton state counts, alphabet size, product-construction size). If the cohort is concentrated at small sizes, ceiling effects are structural and must be flagged as a limitation now, not discovered later.
4. **Generator confounding.** Is any item property systematically associated with ID order? If yes, the deterministic pilot selection in §J must be replaced by a seeded random draw.
5. **Leakage.** Were item contents ever published in a form that could enter a provider's training data? The Zenodo artefact for v1.0.0 is public. Record the publication date against each snapshot's training cutoff, and state the exposure honestly in the limitations. This cannot be undone; it can only be disclosed.

**Conditional rule:** if (2) returns yes for any item, the cohort is outcome-selected and the item random effect no longer generalizes to the generator's population. In that case, and only in that case, regenerate a fresh cohort of 51 equivalence items from the same generator with a new recorded seed, and treat the old cohort as exploratory.

**Generalization target, to state explicitly:** equivalence items produced by generator G under parameters P — not "FSM equivalence problems", and not "formal reasoning tasks".

---

## M. Contract-burden handling

**Keep all six burden metrics descriptive. None enters the primary model.**

**Must NOT be controlled for** — these are post-treatment realizations of the contract, and adjusting for them blocks the very mechanism the contract effect is composed of:

- serialized size of the required witness
- field count
- relation-pair count
- state count of the required witness artefact
- transition count of the required witness artefact
- sequence length

Adjusting for any of these converts the contract effect into "the effect of the contract holding constant the size of the thing the contract requires you to produce", which is close to conditioning the effect away, and additionally opens a collider path if witness size is influenced by both the contract and unmeasured item difficulty.

**Admissible as pre-treatment covariates**, if used at all: properties of the *input* item that exist before any contract is applied — input automaton state counts, alphabet size, size of the product construction, minimal DFA size of the underlying language. These may be used for **pre-specified exploratory effect-modification** analysis (does the contract effect vary with input size?), clearly labelled exploratory, never as adjustment in a primary model.

**Permitted use of burden metrics:** (i) descriptive characterization of what each contract demands, reported in a table; (ii) a clearly-labelled exploratory mediation-flavoured analysis of whether burden tracks the contract effect, with the standard warning that mediation under an unrandomized mediator is not identified here.

---

## N. Ceiling/floor strategy

**Anticipated cells:** T0 witness validity near 0; possibly `minimized_dfa` near 0; possibly extraction near 1.

1. **Do not make a logistic model load-bearing.** Complete separation at 0/51 or 51/51 produces infinite coefficients and boundary-singular random-effect fits. The primary method in §D is a difference of proportions with a bootstrap interval and a permutation test, all of which are well-defined at the boundary. This is a principal reason for that choice.
2. **Marginal rates at the boundary:** Wilson (or Clopper–Pearson where exactness is preferred) intervals; never report 0% or 100% without the interval.
3. **Paired differences at the boundary:** Tango's score interval for the paired risk difference is the recommended reporting standard; it behaves correctly when one or both discordant cells are zero, where Wald and the naive McNemar interval fail.
4. **Bootstrap caution:** BCa can be unstable when the statistic is at a boundary in most resamples. Pre-specify the fallback: if fewer than 5% of resamples produce a non-degenerate statistic, report the Tango score interval as the primary interval for that contrast and say so.
5. **Logistic sensitivity analyses** use Firth penalization or a weakly-informative prior (e.g. Student-t(3, 0, 2.5) on coefficients); a plain `glmer` fit that reports a singular fit is not reported as a result.
6. **Interpretability rule.** A cell at exactly 0/51 across all repetitions and both conditions carries **no** information about the contrast and must be reported as such: "the contrast is not estimable in this condition because the outcome did not occur". Do not report a difference of 0.0 pp with a symmetric interval as though it were evidence of equivalence.
7. **Conditional metrics:** do not report a conditional rate when its denominator is below 10; report the raw counts instead.

---

## O. Sensitivity / detectable effects

No simulation has been run, so no exact power figure is claimed. The following is the exact discordant-pair arithmetic, which is the binding constraint in a paired binary design and does not depend on simulation.

**Hard floor.** Under the exact conditional (McNemar) test at α = 0.05 two-sided, with d discordant items and x of them favouring one direction, the p-value is 2·P(X ≥ x | Bin(d, 0.5)). Therefore:

- d = 5: even a perfect 5–0 split gives p = 0.0625. **Not significant, ever.**
- d = 6: 6–0 gives p = 0.031. This is the minimum detectable configuration, corresponding to an absolute difference of 6/51 ≈ **11.8 pp**.

**Approximate power at α = 0.05 (unadjusted), by scenario:**

| Discordant items d | True split favouring one side | Required majority x | Approx. power | Implied absolute difference |
|---|---|---|---|---|
| 5 | any | — | **0** | ≤ 9.8 pp |
| 10 | 90/10 | ≥ 9 | ≈ 0.74 | 15.7 pp |
| 15 | 80/20 | ≥ 12 | ≈ 0.65 | 17.6 pp |
| 20 | 75/25 | ≥ 15 | ≈ 0.59 | 19.6 pp |
| 20 | 85/15 | ≥ 15 | ≈ 0.93 | 27.5 pp |

Under Holm within a model (smallest α = 0.0167), each of these drops by roughly 10–15 percentage points of power.

**Two corrections that improve on this table.** (i) The primary analysis uses *graded* per-item differences rather than a dichotomized majority, which recovers information from 2/3-vs-1/3 style items and is strictly more powerful than the McNemar arithmetic above; the table is therefore a conservative floor. (ii) k = 5 sharpens the per-item proportions and slightly increases the effective discordance signal. Neither changes the order of magnitude.

**Answer to the question asked: are 51 items enough?**

- **RQ2 (contract effect): yes, if the effect is large**, which is the a priori expectation — the two contracts demand structurally different artefacts. The design has adequate power for absolute differences of ~20 pp and above.
- **RQ3 T0 → T1: probably yes**, if a stepping tool matters at all it should matter substantially.
- **RQ3 T1 → T3 on `witness_valid_first`: marginal.** This is the contrast most likely to be genuinely small, and the design cannot reliably detect a 10 pp effect. Pre-specify that this contrast is reported as estimation with an interval and that "inconclusive" is an acceptable, pre-committed outcome.
- **For any null claim: no.** 51 items cannot support equivalence testing. The CI half-width at the boundary of usefulness is roughly ±10–13 pp, so the tightest honest null statement available is "no difference larger than about 20 pp was detected". This must be written into the pre-spec now so it cannot be quietly upgraded to "no difference" after the fact.

Do **not** add items to chase power on T1 → T3. The correct response is the narrower claim, not a larger cohort — the cohort is not the limiting factor for the questions actually worth asking.

---

## P. Falsification criteria

Each criterion has a statistical component and a practical-effect-size component, and both must be met. "p > .05" is never sufficient.

### Pipeline-level falsifiers (checked first; failure invalidates everything downstream)

- **F0a.** `digest_control` witness validity > 0 in any cell → the verifier accepts an infeasible contract; the entire run is invalid and no RQ is reported.
- **F0b.** Any deterministic sentinel test fails → run invalid.
- **F0c.** The RQ2 negative control (§D) shows a material contract effect on `verdict_correct` (|Δ| > 10 pp with an interval excluding 0) → the contract manipulation is not orthogonal to the verdict path; the RQ2 causal reading is withdrawn and the result is reported as a confound.
- **F0d.** Differential infrastructure loss > 5 pp between contrasted conditions and a tipping-point analysis that flips the sign → contrast reported as inconclusive.

### RQ1

RQ1 makes no causal claim and cannot be falsified statistically, but it can be rendered uninformative: if more than 90% of the outcome mass sits in a single first-failure cell in both models, the decomposition is degenerate and must be reported as such rather than presented as a structured taxonomy. The interesting content of RQ1 is *whether the mass is spread*; a pre-commitment to reporting a degenerate result as degenerate is the honest form of this RQ.

### RQ2 — contract sensitivity

- **Claim supported:** |Δ̂| ≥ 15 pp, permutation p below the Holm-adjusted threshold, same sign in both snapshots.
- **Claim weakened to snapshot-specific:** criteria met in one snapshot only.
- **Claim abandoned ("no meaningful contract sensitivity detected"):** |Δ̂| < 10 pp **and** the 95% interval contained within ±20 pp, in both snapshots. Wording is fixed in advance as: *no contract sensitivity larger than 20 pp was detected under this evaluation setting*, and may not be strengthened.
- **Inconclusive** (a legitimate, pre-committed outcome): everything else — notably |Δ̂| between 10 and 15 pp, or an interval wider than ±20 pp.
- **Structural non-result:** if witness validity is 0 in both contracts, the contrast is not estimable and RQ2 returns "not estimable at this capability level", not "no effect".

### RQ3 — non-answer-producing tool support

- **T0 → T1 claim supported:** Δ̂ ≥ 10 pp, permutation p below the Holm-adjusted threshold, same sign in both snapshots.
- **T1 → T3 claim supported:** Δ̂ ≥ 10 pp on **both** `witness_valid` and `witness_valid_first`, both below the Holm-adjusted threshold, same sign in both snapshots.
- **T1 → T3 claim reduced to a search claim:** effect present on `witness_valid` but absent (|Δ̂| < 5 pp) on `witness_valid_first`. Pre-committed conclusion: *bounded acceptance feedback enables successful search over candidate witnesses; it does not improve first-attempt witness construction.*
- **Claim abandoned ("non-answer-producing tool support does not materially improve witness validity"):** Δ̂ ≤ 5 pp with the interval's upper bound below 15 pp, on both outcomes, in both snapshots.
- **Confound-driven:** if the T3 effect is concentrated in generations that used the full verifier-call budget, and disappears among generations that used one call, the effect is attributed to attempt count and reported as such.

---

## Q. Confirmatory hierarchy

**Tier 0 — Validity gates.** Sentinel tests; `digest_control` = 0; fingerprint match across all runs; infrastructure-loss balance; RQ2 verdict negative control. All reported before any substantive result. Failure of a Tier-0 gate blocks the corresponding claims.

**Tier 1 — Primary confirmatory.** Outcome: `witness_valid` (plus `witness_valid_first` as co-primary for T1→T3). Per model, Holm over three contrasts:
1. RQ2 contract effect (bisimulation vs minimized_dfa, T1 fixed)
2. RQ3 T0 vs T1 (bisimulation fixed)
3. RQ3 T1 vs T3 (bisimulation fixed), co-primary on both outcomes

**Tier 2 — Descriptive primary (no tests).** RQ1 decomposition over the common `n_attempted` denominator, on the 100-item universe, as a composition with simultaneous intervals, per model, per condition. This is reported as the paper's descriptive backbone and is explicitly not a hypothesis test. Verdict accuracy and response bias are estimated here — and only here.

**Tier 3 — Secondary, pre-specified, estimation only, no FWER claim.** `fully_correct` as an outcome for all three primary contrasts; T0 vs T3; between-model difference in each contrast (the interaction estimand); conditional metrics `P(witness_valid | verdict_correct)` and `P(witness_valid | extractable)` with printed denominators and the post-treatment-conditioning caveat; first-failure redistribution across conditions; verifier-call distributions; run-to-run instability (flip rates), which is confirmatory-grade only if k = 5 and descriptive otherwise.

**Tier 4 — Exploratory, labelled as such in every table caption.** Pre-treatment item-size effect modification; burden-metric associations; per-item failure taxonomy; qualitative inspection of failure transcripts; any comparison to the legacy v1 data (which is excluded from all causal claims and may appear only in a clearly separated subsection).

**Rule that makes the hierarchy real:** the tier of every reported number is recorded in the pre-spec, and any analysis not listed in Tiers 0–3 appears in the paper under an "Exploratory" heading, without p-values, regardless of how interesting it turns out to be.

---

## R. PRE_SPECIFICATION.md fields

Freeze the following, in a version-controlled file, tagged in git before the first confirmatory generation. Field names given so the file can be written directly.

```
# Identification
spec_version                     # semver; incremented by any change, with changelog
spec_frozen_at                   # ISO timestamp
git_tag                          # tag at which analysis code was frozen
harness_commit                   # exact commit of the frozen harness
experiment_fingerprint           # hash covering prompt skeleton, parser, verifier,
                                 #   orchestration, tool definitions, decoding config
analysis_code_commit             # analysis pipeline, tested on simulated + permuted data only

# Scientific content
research_questions               # RQ1 (descriptive), RQ2, RQ3 verbatim
hypotheses                       # directional or non-directional, stated per contrast
inferential_scope_statement      # the exact paragraph in section F

# Materials
item_generator                   # generator id, parameters, seed
item_ids_equivalence[51]         # full enumerated list
item_ids_distinguishing[49]      # full enumerated list (RQ1 only)
item_provenance_audit            # answers to K1-K5, including outcome-dependent-filtering answer
item_public_exposure             # Zenodo/GitHub publication dates vs. model cutoffs

# Models
model_ids                        # provider, model string, pinned snapshot id
collection_window                # planned start/end dates
provider_caching                 # disabled | recorded (with field name)

# Conditions
conditions                       # (contract x tool palette) cells enumerated, with fingerprints
contract_definitions             # bisimulation, minimized_dfa, digest_control
tool_palettes                    # T0_NONE, T1_STEP, T3_VERIFY definitions
max_verifier_calls               # integer cap for T3 (recommended 3)
oracle                           # none
format_enforcement               # off

# Execution
k                                # repetitions per cell (recommended 5)
temperature                      # 0.2
max_tokens                       # integer cap; hitting it is an OUTCOME
decoding_params                  # top_p, seed policy, any other sampling parameter
execution_order_seed             # seed for the interleaving shuffle
execution_order_policy           # fully shuffled across item x model x condition x rep
retry_rules                      # backoff schedule, max_reruns = 3, same-index policy

# Outcomes
primary_outcome                  # witness_valid
coprimary_outcome_T3             # witness_valid_first
secondary_outcomes               # fully_correct, extractable, verdict_correct, first-failure
denominator_definition           # n_attempted, defined by the classification table
conditional_outcomes             # with minimum denominator = 10 rule

# Analysis
experimental_unit                # item, within model
stage1_collapse                  # per-item per-condition proportion
primary_estimand                 # mean paired risk difference, percentage points
primary_test                     # within-item sign-flip permutation, 10,000 draws
permutation_seed
interval_method                  # BCa bootstrap over items, 10,000 resamples
bootstrap_seed
boundary_fallback                # Tango score interval, trigger condition
sensitivity_analyses             # majority-vote McNemar+Tango; penalized GLMM; complete-k subset
model_handling                   # separate per snapshot; replication as reporting rule
effect_size_primary              # paired risk difference (absolute)
effect_size_secondary            # matched OR, discordant-pair counts
multiplicity                     # Holm within model over 3 contrasts; intervals nominal
interaction_handling             # estimated, not tested

# Data handling
missingness_classification_table # the full table in section I, verbatim
infrastructure_vs_outcome_rule   # deterministic mapping from finish_reason/exception
item_retention_rule              # >= 2 valid generations in every condition of the family
exclusion_escalation             # >10% exclusions triggers tipping-point analysis
loss_balance_threshold           # 5 pp differential loss triggers caveat + sensitivity

# Pilot
pilot_item_ids[5]                # enumerated, selected deterministically
pilot_k                          # 2
pilot_permitted_metrics          # whitelist; condition-wise outcome rates prohibited
pilot_data_disposition           # excluded from confirmatory analysis
pilot_items_disposition          # retained in confirmatory cohort
post_pilot_mutable_fields        # explicit whitelist
post_pilot_immutable_fields      # explicit blacklist

# Decision rules
validity_gates                   # F0a-F0d
falsification_thresholds         # per RQ, statistical + practical, verbatim from section P
inconclusive_definition          # explicit, per contract
null_claim_wording               # the exact permitted sentence, pre-approved
confirmatory_hierarchy           # Tiers 0-4 with every analysis assigned
exploratory_analyses             # enumerated and labelled; open-ended additions allowed
                                 #   only under the Exploratory heading, without p-values

# Governance
ai_assistance_declaration        # tooling used for harness/analysis code, per ACM policy
                                 #   (14-May-2026), to be carried into the submission
```

---

## S. Final decision

**C. Requires meaningful redesign before collection.**

The redesign is targeted, not structural. The harness itself is sound; what is not yet sound is the measurement contract for T3, the execution schedule, and the outcome/claim structure. All four blockers below are cheap to implement and impossible to repair after data exists.

### MUST CHANGE BEFORE DATA COLLECTION

1. **Cap, log, and instrument the T3 verifier channel.** Pre-specify `max_verifier_calls`; log calls per generation; add the silent `witness_valid_first` outcome; make it co-primary for T1→T3. Without this, the headline RQ3 contrast is partly tautological. *(A1)*
2. **Interleave execution and neutralize caching.** Shuffle the full (item × model × condition × repetition) task list under a recorded seed; timestamp every generation; disable provider prompt caching or record cache status. *(A2)*
3. **Reduce to a single primary outcome and remove verdict accuracy from the 51-item universe.** `witness_valid` is primary; `verdict_correct` is estimable only on the 100-item RQ1 universe where response bias is identified; conditional metrics are descriptive with printed denominators. *(A3, A7, A8)*
4. **Complete the item provenance audit and write the answers down**, in particular whether any item was ever removed on the basis of observed model performance. If yes, regenerate the cohort. *(A12)*
5. **Freeze the missingness classification table in the harness**, so class assignment happens at generation time from machine-readable fields, not afterwards by a human. This is the specific failure mode the previous submission was criticized for. *(A15)*

### SHOULD PRE-SPECIFY

- Experimental unit = item, and the two-stage collapse (§B, §D).
- k = 5, or k = 3 with the instability claim explicitly demoted to descriptive (§C).
- The primary estimand, permutation test, bootstrap intervals and all seeds (§D, §E).
- Per-model analysis with the exact scope-of-inference paragraph (§F).
- Paired risk difference as the primary effect size; absolute over relative (§G).
- Holm within model over three contrasts; intervals nominal and labelled as such (§H).
- The rerun policy, item retention rule and tipping-point escalation (§J).
- The pilot whitelist/blacklist and the blinding of pilot outputs (§K).
- Burden metrics as descriptive only, with the explicit do-not-adjust list (§M).
- Boundary methods and the "not estimable" reporting rule for all-zero cells (§N).
- Falsification thresholds, the pre-approved null-claim wording, and "inconclusive" as a legitimate outcome (§P).
- The Tier 0–4 hierarchy with every planned analysis assigned to a tier (§Q).
- Analysis code written and frozen against simulated and permuted data before unblinding (A18).
- The AI-assistance declaration for harness and analysis code, prepared now rather than at submission.

### DO NOT ADD

- More models "for breadth". Two pinned snapshots with an honest scope statement beat six with a vague one, and the previous submission's six-model spread did not save it.
- More items to chase power on T1 → T3. The correct fix is the narrower claim.
- Adaptive repetition. Outcome-dependent stopping is exactly the degree of freedom this exercise exists to remove.
- An omnibus test before the two RQ3 contrasts. It costs power and answers nothing.
- Intermediate tool palettes (T2, etc.) to "complete the ladder". The ladder is not ordinal, and each rung is another contrast.
- Burden metrics as covariates in any primary model.
- Additional witness contracts beyond the two feasible ones plus the digest control.
- Any comparison against legacy v1 data inside the confirmatory narrative.
- Equivalence/TOST testing at n = 51. The design cannot support it, and attempting it invites a reviewer to compute the achievable bound and print it in the review.
