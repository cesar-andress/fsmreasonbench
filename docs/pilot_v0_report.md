# FSMReasonBench Pilot v0 Report

## Run configuration

- **Model:** `qwen2.5-coder:7b`
- **Temperature:** 0.0
- **Items per family:** 20

## C2 summary

| Metric | Value |
|--------|------:|
| n | 20 |
| extractability_rate | 1.000 |
| verdict_accuracy | 0.750 |
| certificate_valid_rate | 0.100 |
| fully_correct_rate | 0.100 |

### Failure stage counts

| Stage | Count |
|-------|------:|
| not_extractable | 0 |
| verdict_wrong | 5 |
| certificate_invalid | 13 |
| correct | 2 |

### Top certificate failure reasons

| Reason | Count |
|--------|------:|
| trace symbols must be strings | 14 |
| missing reachable states: ['q2', 'q4'] | 1 |
| missing reachable states: ['q2', 'q3', 'q4'] | 1 |
| extra non-reachable states: ['q1'] | 1 |
| missing reachable states: ['q4'] | 1 |

### Sample failures

#### verdict_wrong

- `ba3cc0c9-1732-541d-baed-20703ee26c4c`
  - verdict_correct: False
  - certificate_valid: False
  - certificate_errors: ['trace symbols must be strings']
  - raw_response excerpt: `{
  "item_id": "ba3cc0c9-1732-541d-baed-20703ee26c4c",
  "verdict": true,
  "certificate": {
    "certificate_type": "trace_witness",
    "version": "1.0",
    "payload": {
      "trace": [
        {
`
  - parsed_submission: `{"certificate": {"certificate_type": "trace_witness", "payload": {"state_sequence": ["q0", "q3"], "trace": [{"input": "b", "state": "q0"}, {"input": "a", "state": "q3"}]}, "version": "1.0"}, "item_id"`
- `5db35a30-0f23-5a19-ba28-9c66e2f9cd32`
  - verdict_correct: False
  - certificate_valid: False
  - certificate_errors: ['trace symbols must be strings']
  - raw_response excerpt: `{
  "item_id": "5db35a30-0f23-5a19-ba28-9c66e2f9cd32",
  "verdict": true,
  "certificate": {
    "certificate_type": "trace_witness",
    "version": "1.0",
    "payload": {
      "trace": [
        {
`
  - parsed_submission: `{"certificate": {"certificate_type": "trace_witness", "payload": {"state_sequence": ["q0", "q0"], "trace": [{"input": "a", "state": "q0"}, {"input": "c", "state": "q0"}]}, "version": "1.0"}, "item_id"`
- `e03698a4-1816-51c7-a275-7dea05584b95`
  - verdict_correct: False
  - certificate_valid: False
  - certificate_errors: ['trace symbols must be strings']
  - raw_response excerpt: `{
  "item_id": "e03698a4-1816-51c7-a275-7dea05584b95",
  "verdict": true,
  "certificate": {
    "certificate_type": "trace_witness",
    "version": "1.0",
    "payload": {
      "trace": [
        {
`
  - parsed_submission: `{"certificate": {"certificate_type": "trace_witness", "payload": {"state_sequence": ["q0", "q1"], "trace": [{"input": "a", "state": "q0"}, {"input": null, "state": "q1"}]}, "version": "1.0"}, "item_id`
- `50c54614-4655-55ba-a09a-a3c49f84fa0a`
  - verdict_correct: False
  - certificate_valid: False
  - certificate_errors: ['trace symbols must be strings']
  - raw_response excerpt: `{
  "item_id": "50c54614-4655-55ba-a09a-a3c49f84fa0a",
  "verdict": true,
  "certificate": {
    "certificate_type": "trace_witness",
    "version": "1.0",
    "payload": {
      "trace": [
        {
`
  - parsed_submission: `{"certificate": {"certificate_type": "trace_witness", "payload": {"state_sequence": ["q0", "q1", "q2", "q3"], "trace": [{"input": "a", "state": "q0"}, {"input": "b", "state": "q1"}, {"input": "c", "st`
- `76eab108-3226-5814-bd32-f910a86db134`
  - verdict_correct: False
  - certificate_valid: False
  - certificate_errors: ['trace symbols must be strings']
  - raw_response excerpt: `{
  "item_id": "76eab108-3226-5814-bd32-f910a86db134",
  "verdict": true,
  "certificate": {
    "certificate_type": "trace_witness",
    "version": "1.0",
    "payload": {
      "trace": [
        {
`
  - parsed_submission: `{"certificate": {"certificate_type": "trace_witness", "payload": {"state_sequence": ["q0", "q2", "q4"], "trace": [{"input": "c", "state": "q0"}, {"input": "a", "state": "q2"}, {"input": "c", "state": `

#### certificate_invalid

- `3af8a71a-b8b1-5033-b939-1b1b6f16207f`
  - verdict_correct: True
  - certificate_valid: False
  - certificate_errors: ['trace symbols must be strings']
  - raw_response excerpt: `{
  "item_id": "3af8a71a-b8b1-5033-b939-1b1b6f16207f",
  "verdict": true,
  "certificate": {
    "certificate_type": "trace_witness",
    "version": "1.0",
    "payload": {
      "trace": [
        {
`
  - parsed_submission: `{"certificate": {"certificate_type": "trace_witness", "payload": {"state_sequence": ["q0", "q2", "q3"], "trace": [{"input": "a", "state": "q0"}, {"input": "b", "state": "q2"}, {"input": "c", "state": `
- `0bd7e316-1a35-577d-9ca7-37f49e9b6c69`
  - verdict_correct: True
  - certificate_valid: False
  - certificate_errors: ["missing reachable states: ['q2', 'q4']"]
  - raw_response excerpt: `{
  "item_id": "0bd7e316-1a35-577d-9ca7-37f49e9b6c69",
  "verdict": false,
  "certificate": {
    "certificate_type": "unreachability_witness",
    "version": "1.0",
    "payload": {
      "reachable_`
  - parsed_submission: `{"certificate": {"certificate_type": "unreachability_witness", "payload": {"reachable_states": ["q0"], "target_state": "q1"}, "version": "1.0"}, "item_id": "0bd7e316-1a35-577d-9ca7-37f49e9b6c69", "ver`
- `96ba0e25-c1b9-5ab2-8e1f-8b81205ba6ac`
  - verdict_correct: True
  - certificate_valid: False
  - certificate_errors: ['trace symbols must be strings']
  - raw_response excerpt: `{
  "item_id": "96ba0e25-c1b9-5ab2-8e1f-8b81205ba6ac",
  "verdict": true,
  "certificate": {
    "certificate_type": "trace_witness",
    "version": "1.0",
    "payload": {
      "trace": [
        {
`
  - parsed_submission: `{"certificate": {"certificate_type": "trace_witness", "payload": {"state_sequence": ["q0", "q3"], "trace": [{"input": "c", "state": "q0"}, {"input": "b", "state": "q3"}]}, "version": "1.0"}, "item_id"`
- `716ba5ba-81cd-5097-b8df-17488c62ff0f`
  - verdict_correct: True
  - certificate_valid: False
  - certificate_errors: ["missing reachable states: ['q2', 'q3', 'q4']"]
  - raw_response excerpt: `{
  "item_id": "716ba5ba-81cd-5097-b8df-17488c62ff0f",
  "verdict": false,
  "certificate": {
    "certificate_type": "unreachability_witness",
    "version": "1.0",
    "payload": {
      "reachable_`
  - parsed_submission: `{"certificate": {"certificate_type": "unreachability_witness", "payload": {"reachable_states": ["q0"], "target_state": "q1"}, "version": "1.0"}, "item_id": "716ba5ba-81cd-5097-b8df-17488c62ff0f", "ver`
- `2fbc4c9c-454b-5828-b08d-0eb7432a31fe`
  - verdict_correct: True
  - certificate_valid: False
  - certificate_errors: ['trace symbols must be strings']
  - raw_response excerpt: `{
  "item_id": "2fbc4c9c-454b-5828-b08d-0eb7432a31fe",
  "verdict": true,
  "certificate": {
    "certificate_type": "trace_witness",
    "version": "1.0",
    "payload": {
      "trace": [
        {
`
  - parsed_submission: `{"certificate": {"certificate_type": "trace_witness", "payload": {"state_sequence": ["q0", "q3"], "trace": [{"input": "b", "state": "q0"}, {"input": "a", "state": "q3"}]}, "version": "1.0"}, "item_id"`

## F1 summary

| Metric | Value |
|--------|------:|
| n | 20 |
| extractability_rate | 1.000 |
| verdict_accuracy | 1.000 |
| certificate_valid_rate | 0.050 |
| fully_correct_rate | 0.050 |

### Failure stage counts

| Stage | Count |
|-------|------:|
| not_extractable | 0 |
| verdict_wrong | 0 |
| certificate_invalid | 19 |
| correct | 1 |

### Top certificate failure reasons

| Reason | Count |
|--------|------:|
| trace replay failed: no transition from 'q0' on 'a' | 7 |
| trace replay failed: no transition from 'q2' on 'b' | 4 |
| acceptance.A mismatch: replay=True, declared=False | 2 |
| trace replay failed: no transition from 'q0' on 'b' | 2 |
| trace replay failed: no transition from 'q3' on 'b' | 1 |
| trace replay failed: no transition from 'q1' on 'c' | 1 |
| acceptance.A mismatch: replay=False, declared=True | 1 |
| trace replay failed: no transition from 'q1' on 'b' | 1 |

### Sample failures

#### certificate_invalid

- `16fee15f-15bf-57f6-ad8d-9a82201f0b02`
  - verdict_correct: True
  - certificate_valid: False
  - certificate_errors: ["trace replay failed: no transition from 'q0' on 'a'"]
  - raw_response excerpt: ````json
{
  "item_id": "16fee15f-15bf-57f6-ad8d-9a82201f0b02",
  "verdict": false,
  "certificate": {
    "certificate_type": "distinguishing_trace",
    "version": "1.0",
    "fsm_ids": ["10f6860f-2b`
  - parsed_submission: `{"certificate": {"certificate_type": "distinguishing_trace", "fsm_ids": ["10f6860f-2bfa-55f6-b6c3-170b9223c0a2", "3f731e9c-fe61-5f34-be91-d4201bda022c"], "payload": {"acceptance": {"A": false, "B": tr`
- `08cf0120-b857-5984-8cb4-e9916b9cce3b`
  - verdict_correct: True
  - certificate_valid: False
  - certificate_errors: ["trace replay failed: no transition from 'q0' on 'a'"]
  - raw_response excerpt: ````json
{
  "item_id": "08cf0120-b857-5984-8cb4-e9916b9cce3b",
  "verdict": false,
  "certificate": {
    "certificate_type": "distinguishing_trace",
    "version": "1.0",
    "fsm_ids": ["c47db9c5-e8`
  - parsed_submission: `{"certificate": {"certificate_type": "distinguishing_trace", "fsm_ids": ["c47db9c5-e80e-5d73-ba6d-78dfa542b667", "4020ebab-997f-5502-93ff-76c12ca62684"], "payload": {"acceptance": {"A": false, "B": tr`
- `a3553aa3-1550-5e9a-9046-6515a569d4bd`
  - verdict_correct: True
  - certificate_valid: False
  - certificate_errors: ["trace replay failed: no transition from 'q2' on 'b'"]
  - raw_response excerpt: ````json
{
  "item_id": "a3553aa3-1550-5e9a-9046-6515a569d4bd",
  "verdict": false,
  "certificate": {
    "certificate_type": "distinguishing_trace",
    "version": "1.0",
    "fsm_ids": ["b9088544-1f`
  - parsed_submission: `{"certificate": {"certificate_type": "distinguishing_trace", "fsm_ids": ["b9088544-1f84-5997-af39-b08c3ffee88f", "c348da51-2d0b-5eef-82a4-d61594945c0d"], "payload": {"acceptance": {"A": false, "B": tr`
- `0ebd4577-8958-5041-bd45-4e76a4e3a9f9`
  - verdict_correct: True
  - certificate_valid: False
  - certificate_errors: ["trace replay failed: no transition from 'q2' on 'b'"]
  - raw_response excerpt: ````json
{
  "item_id": "0ebd4577-8958-5041-bd45-4e76a4e3a9f9",
  "verdict": false,
  "certificate": {
    "certificate_type": "distinguishing_trace",
    "version": "1.0",
    "fsm_ids": ["6e3d1949-d0`
  - parsed_submission: `{"certificate": {"certificate_type": "distinguishing_trace", "fsm_ids": ["6e3d1949-d0b9-5a28-bc15-fbe08de04abd", "41b90ab6-bab6-50d0-833b-68f41606c97d"], "payload": {"acceptance": {"A": false, "B": tr`
- `ac50ad35-8941-5eb3-9f73-cdf57e318c34`
  - verdict_correct: True
  - certificate_valid: False
  - certificate_errors: ["trace replay failed: no transition from 'q3' on 'b'"]
  - raw_response excerpt: ````json
{
  "item_id": "ac50ad35-8941-5eb3-9f73-cdf57e318c34",
  "verdict": false,
  "certificate": {
    "certificate_type": "distinguishing_trace",
    "version": "1.0",
    "fsm_ids": ["b1ef6cc7-48`
  - parsed_submission: `{"certificate": {"certificate_type": "distinguishing_trace", "fsm_ids": ["b1ef6cc7-48c7-5580-a773-9e141c3b516b", "7a6b4dce-a07d-56d1-98ed-6504a9d375ec"], "payload": {"acceptance": {"A": false, "B": tr`

## Interpretation

Verdict accuracy overstates reasoning success: the model often emits extractable JSON and correct high-level verdicts while failing to produce executable certificates.

## Representative failure modes

- **C2:** C2 trace payload uses objects instead of symbol strings
- **C2:** C2 unreachability witness omits reachable states
- **F1:** F1 repeatedly emits generic traces such as ["a", "b"] that are not replayable
