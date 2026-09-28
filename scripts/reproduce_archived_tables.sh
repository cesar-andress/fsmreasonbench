#!/usr/bin/env bash
# Venue-neutral entry point: offline regeneration of layered evaluation tables/figures
# from frozen archived outputs. Does NOT call model APIs.
#
# Implementation: delegates to the historical script name retained for path stability.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$REPO_ROOT/scripts/reproduce_tosem_tables.sh" "$@"
