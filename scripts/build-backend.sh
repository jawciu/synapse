#!/usr/bin/env bash
set -euo pipefail

# Bootstrap the patched installer from the Python security announcement, verifying
# its SHA-256 before executing it. Do not use Render's potentially stale pip/uv.
build_tools=$(mktemp -d)
trap 'rm -rf "$build_tools"' EXIT
curl --fail --silent --show-error --location \
  https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl \
  --output "$build_tools/pip.whl"
python - "$build_tools" <<'PY'
import hashlib
import pathlib
import sys
import zipfile

root = pathlib.Path(sys.argv[1])
wheel = root / "pip.whl"
expected = "fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"
if hashlib.sha256(wheel.read_bytes()).hexdigest() != expected:
    raise SystemExit("Patched pip wheel checksum mismatch")
zipfile.ZipFile(wheel).extractall(root / "bootstrap")
PY
PYTHONPATH="$build_tools/bootstrap" python -m pip install \
  --target "$build_tools/tools" 'uv==0.13.4'
"$build_tools/tools/bin/uv" sync --frozen --group security
