#!/usr/bin/env bash
# One-command installer for the standalone `providence` CLI binary.
#
# Installs `providence` only — it does not fetch or manage `sdd-compile`. `sdd`
# resolves `sdd-compile` on its own at runtime (env var, local build, PATH,
# wheel-bundled asset, or a verified version-tagged download), unchanged by
# this installer. See packages/core/providence_core/src/providence_core/utils/compiler_runner.py.
#
# Versioning: defaults to the latest GitHub release. Pass --version <tag> to
# pin a specific release. Rollback is re-running this script with
# --version <previous-tag> — there is no separate rollback command.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/SergioLacerda/providence/main/install.sh | bash
#   ./install.sh --version v1.2.3
#   ./install.sh --dir /custom/bin/path

set -euo pipefail

REPO="SergioLacerda/providence"
INSTALL_DIR="${SDD_INSTALL_DIR:-$HOME/.local/bin}"
# Override point for CI smoke coverage: release assets don't exist yet at
# smoke-test time (this script's own release job hasn't published them), so
# CI points this at a local server serving the freshly built dist/ instead.
# Unset in normal use — real installs always hit the real GitHub release.
BASE_URL_OVERRIDE="${SDD_INSTALL_BASE_URL:-}"
VERSION=""

usage() {
  cat <<'EOF'
Usage: install.sh [--version <tag>] [--dir <path>]

  --version <tag>   Install a specific release tag (e.g. v1.2.3). Defaults to
                     the latest release. Also how you roll back: re-run with
                     the previous tag.
  --dir <path>      Install location. Defaults to $HOME/.local/bin
                     (or $SDD_INSTALL_DIR if set).
  -h, --help        Show this help and exit.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --version)
      VERSION="$2"
      shift 2
      ;;
    --dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

detect_asset_name() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"
  case "$os" in
    Linux)
      case "$arch" in
        x86_64|amd64) echo "providence-linux-amd64" ;;
        *)
          echo "ERROR: unsupported Linux architecture: $arch (only x86_64 is published)" >&2
          exit 1
          ;;
      esac
      ;;
    Darwin)
      case "$arch" in
        arm64) echo "providence-darwin-arm64" ;;
        x86_64)
          echo "ERROR: no providence-darwin-amd64 asset is published (PyInstaller can't" >&2
          echo "cross-compile, and GitHub-hosted macOS runners are arm64-only)." >&2
          echo "Install via 'uv tool install providence-cli' or pipx instead on Intel Macs." >&2
          exit 1
          ;;
        *)
          echo "ERROR: unsupported macOS architecture: $arch" >&2
          exit 1
          ;;
      esac
      ;;
    *)
      echo "ERROR: unsupported OS: $os (use install.ps1 on Windows)" >&2
      exit 1
      ;;
  esac
}

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "ERROR: neither sha256sum nor shasum is available to verify the download" >&2
    exit 1
  fi
}

resolve_tag() {
  if [ -n "$VERSION" ]; then
    echo "$VERSION"
    return
  fi
  local tag
  tag=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
    | grep -m1 '"tag_name"' | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')
  if [ -z "$tag" ]; then
    echo "ERROR: could not resolve the latest release tag from the GitHub API" >&2
    exit 1
  fi
  echo "$tag"
}

# Not local to main(): the EXIT trap below runs at global scope even when
# main() aborts mid-execution under `set -e`, so `set -u` would otherwise
# reject it as an unbound variable once main()'s local scope is torn down.
tmp_dir=""

main() {
  local asset tag base_url sums_file expected_sum actual_sum

  asset="$(detect_asset_name)"

  if [ -n "$BASE_URL_OVERRIDE" ]; then
    tag="local"
    base_url="$BASE_URL_OVERRIDE"
  else
    tag="$(resolve_tag)"
    base_url="https://github.com/${REPO}/releases/download/${tag}"
  fi

  echo "Installing providence ${tag} (${asset}) to ${INSTALL_DIR}"

  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "$tmp_dir"' EXIT

  echo "Downloading ${asset}..."
  curl -fsSL -o "${tmp_dir}/${asset}" "${base_url}/${asset}"

  sums_file="${tmp_dir}/SHA256SUMS"
  echo "Downloading SHA256SUMS..."
  curl -fsSL -o "$sums_file" "${base_url}/SHA256SUMS"

  expected_sum="$(grep " ${asset}\$" "$sums_file" | awk '{print $1}')"
  if [ -z "$expected_sum" ]; then
    echo "ERROR: SHA256SUMS for ${tag} has no entry for ${asset}" >&2
    exit 1
  fi
  actual_sum="$(sha256_of "${tmp_dir}/${asset}")"
  if [ "$expected_sum" != "$actual_sum" ]; then
    echo "ERROR: checksum mismatch for ${asset}" >&2
    echo "  expected: ${expected_sum}" >&2
    echo "  actual:   ${actual_sum}" >&2
    exit 1
  fi
  echo "Checksum verified."

  mkdir -p "$INSTALL_DIR"
  install -m 0755 "${tmp_dir}/${asset}" "${INSTALL_DIR}/providence"

  echo "Installed providence ${tag} to ${INSTALL_DIR}/providence"
  case ":$PATH:" in
    *":${INSTALL_DIR}:"*) ;;
    *)
      echo "NOTE: ${INSTALL_DIR} is not on your PATH. Add it, e.g.:"
      echo "  export PATH=\"${INSTALL_DIR}:\$PATH\""
      ;;
  esac
  "${INSTALL_DIR}/providence" version
}

main "$@"
