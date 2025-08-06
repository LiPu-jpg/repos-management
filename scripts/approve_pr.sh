#!/bin/bash

# List of repositories
REPOS=$(cat repos_list.txt) # repos_list.txt 需要和本脚本在同一目录下

# Put your GitHub Personal Access Token in .env file
# Format: PERSONAL_ACCESS_TOKEN=your_token_here
source .env

for REPO in $REPOS; do
  # Fetch number of the PR with '[automated-generate-PR]' in the title
  # By default, fetch the number of the latest PR
  PR_NUMBER=$(gh pr list -R "HITSZ-OpenAuto/$REPO" --search "${PR_MARKER} in:title" --json number -q '.[0].number')

  if [ -z "$PR_NUMBER" ]; then
    echo "No open pull requests found for $REPO"
    continue
  fi

  # Approve the pull request
  gh pr review -R "HITSZ-OpenAuto/$REPO" "$PR_NUMBER" --approve

  # Merge the pull request
  gh pr merge -R "HITSZ-OpenAuto/$REPO" "$PR_NUMBER" --squash --delete-branch --admin

  echo "PR approved and merged for $REPO"
done
