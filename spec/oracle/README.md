# Oracle procedure registry

Placeholder for mapping task families to exact decision procedures and tool versions.

**Status:** not implemented.

Planned file: `procedure_registry.yaml`

Example entry (illustrative):

```yaml
F1:
  procedure: shortest_separation_witness
  subtypes: [F1.a, F1.b, F1.c]
F2:
  procedure: compositional_counterexample
  internal_product: allowed
  submission_product: forbidden
```

See `docs/specification/task_families.md` per-family oracle sections.
