"""Shared LaTeX caption phrasing for frozen n=100 manuscript tables."""

FROZEN_CELL_DENOM_NOTE = (
    "Verdict and Cert.\\ condition on extractable submissions; "
    "Full uses all $n{=}100$ items."
)

FROZEN_TOOL_TRACK_COLUMNS = (
    "Model & Fam. & Track & $n$ & Extract. & Verdict & Cert. & Full"
)

FROZEN_TOOL_TRACK_COLUMNS_WITH_GAP = f"{FROZEN_TOOL_TRACK_COLUMNS} & Gap"


def frozen_n100_caption(focus: str) -> str:
    """Standard opening for comparable frozen-cell rate tables."""
    return f"Frozen $n{{=}}100$, $T{{=}}0.2$: {focus}."
