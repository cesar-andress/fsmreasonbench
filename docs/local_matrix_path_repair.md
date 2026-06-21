# Local Matrix Path Repair

When a matrix cell is written without the required `temp_{temperature}` directory segment, status tools look under the expected path and report the cell as **missing** even though artifacts exist elsewhere.

## Observed symptom

Work landed under:

```text
runs/local_matrix_v1/llama3.1_8b/C2/R1/
```

Expected layout:

```text
runs/local_matrix_v1/llama3.1_8b/C2/temp_0/R1/
```

## Root cause

Older runner logic only enabled `temp_*` directories when more than one temperature was configured (`len(temperatures) > 1`). Single-temperature incremental-safe retries on `local_matrix_v1` therefore wrote to the legacy track-pilot layout.

## Automated repair

Dry run:

```bash
cd ~/papers/fsmreasonbench/fsmreasonbench
PYTHONPATH=src python -m fsmreasonbench.cli.repair_local_matrix_paths \
  --root runs/local_matrix_v1 \
  --dry-run
```

Apply:

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.repair_local_matrix_paths \
  --root runs/local_matrix_v1 \
  --apply
```

The repair tool:

- detects `{model}/{family}/{track}` directories directly under a family folder
- scans **all model directories under `--root`**, not only models listed in `combined_summary.json`
- infers temperature from `cell_status.json` or `error.json`
- merges or moves artifacts into `{model}/{family}/temp_{T}/{track}/`
- merges `scores.jsonl` / `results.jsonl` by `item_id` when the target already exists
- refuses ambiguous moves when temperature cannot be inferred
- refuses conflicting non-JSONL files unless byte-identical
- writes `repair_log.json`

## Manual repair (Llama C2 R1 T=0 example)

If temperature is known to be `0.0` and the misplaced directory contains the only copy of the artifacts:

```bash
cd ~/papers/fsmreasonbench/fsmreasonbench
mkdir -p runs/local_matrix_v1/llama3.1_8b/C2/temp_0
mv runs/local_matrix_v1/llama3.1_8b/C2/R1 \
   runs/local_matrix_v1/llama3.1_8b/C2/temp_0/R1
```

Verify:

```bash
find runs/local_matrix_v1/llama3.1_8b/C2/temp_0/R1 -maxdepth 1 -type f -print
PYTHONPATH=src python -m fsmreasonbench.cli.experiment_status \
  --root runs/local_matrix_v1
```

## Safe re-run after fix

```bash
PYTHONPATH=src python -m fsmreasonbench.cli.run_track_pilot_models \
  --models llama3.1:8b \
  --families C2 \
  --tracks R1 \
  --temperatures 0 \
  --max-items 20 \
  --timeout 900 \
  --out-dir runs/local_matrix_v1 \
  --retry-failed \
  --incremental-safe
```

Verify completed count:

```bash
find runs/local_matrix_v1 -path '*/temp_*/R1/summary.json' | wc -l
find runs/local_matrix_v1/llama3.1_8b/C2/temp_0/R1 -maxdepth 1 -type f -print
```
