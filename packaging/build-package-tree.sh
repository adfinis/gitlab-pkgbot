#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version_arg="${PKGBOT_VERSION:-}"

if [[ "${1:-}" == "--version" ]]; then
  version_arg="${2:?missing version after --version}"
  shift 2
fi

stage="${1:-"$root/build/package-root"}"
wheel_dir="$root/build/wheel"
python_bin="${PYTHON:-/usr/bin/python3}"
purelib="${PURELIB:-/usr/lib/python3/dist-packages}"
raw_version="${version_arg:-0.0.0}"

# Snapshot package versions may be semver-ish, e.g. 1.2.3-SNAPSHOT-abc1234.
# Python wheel metadata needs PEP 440, so keep releases unchanged and convert
# snapshots to a local dev version.
export PKGBOT_VERSION="${raw_version#v}"
if [[ "$PKGBOT_VERSION" == *"-SNAPSHOT-"* ]]; then
  PKGBOT_VERSION="${PKGBOT_VERSION/-SNAPSHOT-/.dev0+}"
  PKGBOT_VERSION="${PKGBOT_VERSION//-/.}"
fi

rm -rf "$stage" "$wheel_dir"
mkdir -p "$stage$purelib" "$stage/usr/bin" "$wheel_dir"

uv build --wheel --out-dir "$wheel_dir"
wheel="$(find "$wheel_dir" -maxdepth 1 -name '*.whl' -print -quit)"
if [[ -z "$wheel" ]]; then
  echo "No wheel produced in $wheel_dir" >&2
  exit 1
fi

uv pip install --no-deps --python "$python_bin" --target "$stage$purelib" "$wheel"

if compgen -G "$stage$purelib/bin/*" >/dev/null; then
  mv "$stage$purelib"/bin/* "$stage/usr/bin/"
  rmdir "$stage$purelib/bin"
fi

rm -rf "$stage$purelib/.lock" "$stage$purelib"/*.dist-info/uv_cache.json
find "$stage/usr/bin" -type f -exec chmod 0755 {} +
