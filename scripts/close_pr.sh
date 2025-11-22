#!/bin/bash

# List of repositories
REPOS=$(cat repos_list.txt) # repos_list.txt 需要和本脚本在同一目录下

# Define PR marker
PR_MARKER="[automated-generated-pr]"

process_repo() {
  local REPO=$1
  # Fetch number of the PR with '[automated-generated-pr]' in the title
  # By default, fetch the number of the latest PR
  local PR_NUMBER=$(gh pr list -R "HITSZ-OpenAuto/$REPO" --search "${PR_MARKER} in:title" --json number -q '.[0].number')

  if [ -z "$PR_NUMBER" ]; then
    echo "No open pull requests found for $REPO"
    return
  fi

  # Close the pull request and delete the branch
  gh pr close -R "HITSZ-OpenAuto/$REPO" "$PR_NUMBER" --delete-branch

  echo "PR closed and branch deleted for $REPO"
}

for REPO in $REPOS; do
  process_repo "$REPO" &
done

wait
