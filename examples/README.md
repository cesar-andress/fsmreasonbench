# Examples

Hand-generated and tool-generated **illustrative items** (not full cohorts).

| File | Description |
|------|-------------|
| `item_C2_reachability_seed42.json` | First self-verifying C2 reachability item (`seed=42`, `\|Q\|=5`) |

Regenerate:

```bash
python3 -m fsmreasonbench.cli.generate_one --seed 42 --output examples/item_C2_reachability_seed42.json
```

Each item passes `self_verify_item`: generator → oracle → certificate → verifier.
