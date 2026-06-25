#!/usr/bin/env bash
# Reproduce deterministic paper tables from archived submissions (R4 tier).
# Delegates to the TOSEM read-only export workflow (no model API calls).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/reproduce_tosem_tables.sh" "$@"
