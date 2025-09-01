#!/usr/bin/env bash
# batch_delete_dirs.sh
set -Euo pipefail  # Removed -e to prevent immediate exit on first error

GITHUB_OWNER="${1:-HITSZ-OpenAuto}"     # org/user
BASE_BRANCH="${2:-main}"
DIR_TO_DELETE="${3:-.hoa}"
SCRIPT="${SCRIPT:-./scripts/delete_dir.sh}"  # your per-repo script that opens a PR

[[ -f repos_list.txt ]] || { echo "ERROR: repos_list.txt not found!"; exit 1; }

# Make gh fully non-interactive
export GH_PROMPT_DISABLED=true
export GIT_EDITOR=:

# Read repos into an array (prevents stdin conflicts)
mapfile -t REPOS < repos_list.txt

# Counters
total=0
success=0
failed=0

echo "Processing ${#REPOS[@]} repositories..."
echo "Owner: $GITHUB_OWNER"
echo "Base branch: $BASE_BRANCH"
echo "Directory to delete: $DIR_TO_DELETE"
echo "---"

for raw in "${REPOS[@]}"; do
  # Trim whitespace and CRLF, skip blanks and comments
  repo="${raw//$'\r'/}"                                  # strip CR
  repo="${repo#"${repo%%[![:space:]]*}"}"                # ltrim
  repo="${repo%"${repo##*[![:space:]]}"}"                # rtrim
  [[ -z "$repo" || "$repo" == \#* ]] && continue

  ((total++))
  echo "[$total] Processing: $repo"

  # IMPORTANT: detach child from stdin so it can't eat our list
  # Add explicit error handling instead of relying on set -e
  if timeout 60 "$SCRIPT" "$GITHUB_OWNER/$repo" "$BASE_BRANCH" "$DIR_TO_DELETE" </dev/null; then
    echo "✓ Success: $repo"
    ((success++))
  else
    exit_code=$?
    if [[ $exit_code -eq 124 ]]; then
      echo "✗ Timeout: $repo (60s limit exceeded)"
    else
      echo "✗ Failed: $repo (exit code: $exit_code)"
    fi
    ((failed++))
  fi

  echo "---"
  sleep 2  # light pacing for rate limits
done

echo "Summary: $success successful, $failed failed (out of $total)"
