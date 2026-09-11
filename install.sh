#!/bin/bash
set -euo pipefail
if (( $# != 1 )); then
  echo "Usage: $0 /path/to/python/kernel-spec" >&2
  exit 1
fi
flinc_source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python "$flinc_source_dir/install_kernels.py" "$1"
