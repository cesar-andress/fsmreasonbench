"""CLI: write frozen confirmatory manifests (no provider calls)."""

from __future__ import annotations

from pathlib import Path

from fsmreasonbench.clean_v2.confirmatory.manifests import generate_manifests
from fsmreasonbench.clean_v2.confirmatory.provenance_audit import write_provenance_audit


def main() -> None:
    repo = Path(__file__).resolve().parents[3]
    # src/fsmreasonbench/cli -> parents[3] is package root? 
    # __file__ = .../src/fsmreasonbench/cli/xxx.py -> parents[0]=cli, [1]=fsmreasonbench, [2]=src, [3]=repo
    audit_path = repo / "docs/clean_v2/ITEM_PROVENANCE_AUDIT.json"
    write_provenance_audit(repo, audit_path)
    result = generate_manifests(repo)
    print(f"Wrote provenance audit to {audit_path}")
    print(f"Wrote manifests to {result['out_dir']}")
    for name, meta in result["written"].items():
        print(f"  {name}: n={meta['n_tasks']} fp={meta['fingerprint'][:16]}… path={meta['path']}")
    print(f"provenance_decision={result['audit_decision']}")


if __name__ == "__main__":
    main()
