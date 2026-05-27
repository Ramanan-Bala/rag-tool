#!/usr/bin/env bash
# Replace repo-rag placeholders with real identity values.
#
# Usage:
#   scripts/replace-placeholders.sh \
#     --github-username octocat \
#     --full-name "Octo Cat" \
#     --email octo@example.com \
#     [--year 2026]

set -euo pipefail

GITHUB_USERNAME=""
FULL_NAME=""
EMAIL=""
YEAR="$(date +%Y)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --github-username) GITHUB_USERNAME="$2"; shift 2 ;;
        --full-name)       FULL_NAME="$2"; shift 2 ;;
        --email)           EMAIL="$2"; shift 2 ;;
        --year)            YEAR="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,11p' "$0"; exit 0 ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2 ;;
    esac
done

if [[ -z "$GITHUB_USERNAME" || -z "$FULL_NAME" || -z "$EMAIL" ]]; then
    echo "Required: --github-username, --full-name, --email" >&2
    exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

SKIP_DIRS=( .git .venv venv env dist build .pytest_cache .ruff_cache .mypy_cache
            node_modules .repo-rag __pycache__ .tox .nox htmlcov .idea )

skip_pattern="$(IFS='|'; echo "${SKIP_DIRS[*]}")"

EXTS_REGEX='\.(py|md|toml|ya?ml|json|cfg|ini|txt|ps1|sh|dockerfile|dockerignore|gitignore|mdc|rules|conf)$'

mapfile -t FILES < <(
    find "$ROOT" -type f \
        | grep -Ev "/($skip_pattern)/" \
        | grep -E "$EXTS_REGEX|/(Dockerfile|LICENSE|CHANGELOG|CONTRIBUTING|SECURITY|CODE_OF_CONDUCT)$"
)

changed=0
for f in "${FILES[@]}"; do
    if grep -q -e '<YOUR_GITHUB_USERNAME>' -e '<YOUR_NAME>' \
              -e '<your.email@example.com>' -e 'noreply@example.com' \
              -e '<YEAR>' "$f" 2>/dev/null; then
        tmp="$(mktemp)"
        sed -e "s|<YOUR_GITHUB_USERNAME>|$GITHUB_USERNAME|g" \
            -e "s|<YOUR_NAME>|$FULL_NAME|g" \
            -e "s|<your.email@example.com>|$EMAIL|g" \
            -e "s|noreply@example.com|$EMAIL|g" \
            -e "s|<YEAR>|$YEAR|g" \
            "$f" > "$tmp"
        if ! cmp -s "$f" "$tmp"; then
            mv "$tmp" "$f"
            changed=$((changed + 1))
            rel="${f#"$ROOT"/}"
            echo "patched: $rel"
        else
            rm -f "$tmp"
        fi
    fi
done

echo ""
echo "Done. Updated $changed files."
