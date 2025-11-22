#!/bin/bash

# Initialize
PR_DESCRIPTION="This PR disables the scheduled trigger in the workflow to prevent GitHub from freezing the workflow runs after 60 days of inactivity."
REPOS=$(cat repos_list.txt)
PR_MARKER="[automated-generated-pr]"
PR_TITLE="${PR_MARKER} ci: disable scheduled trigger"
PR_COMMIT_MESSAGE="ci: disable scheduled trigger"

# Fetch workflow content from the online repository
NEW_WORKFLOW_URL="https://raw.githubusercontent.com/HITSZ-OpenAuto/repos-management/refs/heads/main/call_worktree_update.yml"

echo "Fetching workflow content from $NEW_WORKFLOW_URL"
WORKFLOW_CONTENT=$(curl -sSLf "$NEW_WORKFLOW_URL")

if [ $? -ne 0 ] || [ -z "$WORKFLOW_CONTENT" ]; then
  echo "Error: Failed to fetch workflow content from $NEW_WORKFLOW_URL"
  exit 1
fi

process_repo() {
  local REPO=$1
  echo "Processing $REPO"
    
  local BRANCH_NAME="fix/disable-schedule-worktree"
  # Get the latest commit SHA of the main branch
  local MAIN_SHA
  MAIN_SHA=$(gh api -H "Authorization: token $PERSONAL_ACCESS_TOKEN" "/repos/HITSZ-OpenAuto/$REPO/git/ref/heads/main" -q '.object.sha')

  # Check if the branch already exists
  local BRANCH_CHECK_RESULT
  BRANCH_CHECK_RESULT=$(gh api -H "Authorization: token $PERSONAL_ACCESS_TOKEN" "/repos/HITSZ-OpenAuto/$REPO/git/ref/heads/$BRANCH_NAME" 2>&1)
  local BRANCH_CHECK_EXIT_CODE=$?
  
  local BRANCH_EXISTS="false"
  if [ $BRANCH_CHECK_EXIT_CODE -eq 0 ]; then
    echo "Branch $BRANCH_NAME already exists, skipping branch creation"
    BRANCH_EXISTS="true"
  else
    echo "Creating new branch: $BRANCH_NAME"
    # Create a new branch
    local CREATE_RESULT
    CREATE_RESULT=$(gh api -X POST \
      -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
      -H "Accept: application/vnd.github.v3+json" \
      "/repos/HITSZ-OpenAuto/$REPO/git/refs" \
      -f ref="refs/heads/$BRANCH_NAME" \
      -f sha="$MAIN_SHA" 2>&1)
    local CREATE_EXIT_CODE=$?
    
    if [ $CREATE_EXIT_CODE -eq 0 ]; then
      echo "Branch created successfully"
      BRANCH_EXISTS="true"
    else
      echo "Failed to create branch: $CREATE_RESULT"
      return
    fi
  fi

  # Get the SHA of the existing workflow file if it exists
  local FILE_SHA
  FILE_SHA=$(gh api -H "Authorization: token $PERSONAL_ACCESS_TOKEN" "/repos/HITSZ-OpenAuto/$REPO/contents/.github/workflows/trigger-workflow.yml?ref=$BRANCH_NAME" -q '.sha' 2>/dev/null)
  
  # Check if FILE_SHA is valid (not empty and not a JSON error)
  if [[ "$FILE_SHA" == *"{"* ]]; then
      FILE_SHA=""
  fi
  
  if [ -n "$FILE_SHA" ]; then
    echo "Found existing workflow file with SHA: $FILE_SHA"
  else
    echo "No existing workflow file found, creating new file"
  fi

  # Create or update the workflow file in the branch
  local WORKFLOW_CONTENT_BASE64=$(echo "$WORKFLOW_CONTENT" | base64)
  local UPDATE_RESULT
  local UPDATE_EXIT_CODE
  
  if [ -n "$FILE_SHA" ]; then
    echo "Updating existing workflow file..."
    UPDATE_RESULT=$(gh api -X PUT \
      -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
      -H "Accept: application/vnd.github.v3+json" \
      "/repos/HITSZ-OpenAuto/$REPO/contents/.github/workflows/trigger-workflow.yml" \
      -f message="$PR_COMMIT_MESSAGE" \
      -f content="$WORKFLOW_CONTENT_BASE64" \
      -f branch="$BRANCH_NAME" \
      -f sha="$FILE_SHA" 2>&1)
  else
    echo "Creating new workflow file..."
    UPDATE_RESULT=$(gh api -X PUT \
      -H "Authorization: token $PERSONAL_ACCESS_TOKEN" \
      -H "Accept: application/vnd.github.v3+json" \
      "/repos/HITSZ-OpenAuto/$REPO/contents/.github/workflows/trigger-workflow.yml" \
      -f message="$PR_TITLE" \
      -f content="$WORKFLOW_CONTENT_BASE64" \
      -f branch="$BRANCH_NAME" 2>&1)
  fi
  
  UPDATE_EXIT_CODE=$?
  if [ $UPDATE_EXIT_CODE -eq 0 ]; then
    echo "Workflow file updated successfully for $REPO"
  else
    echo "Failed to update workflow file for $REPO: $UPDATE_RESULT"
    return
  fi

  # Create a pull request
  sleep 5
  local PR_RESULT
  PR_RESULT=$(gh pr create -R "HITSZ-OpenAuto/$REPO" -B main -H "$BRANCH_NAME" -t "$PR_TITLE" -b "$PR_DESCRIPTION" 2>&1)
  local PR_EXIT_CODE=$?
  
  if [ $PR_EXIT_CODE -eq 0 ]; then
    echo "PR created successfully for $REPO: $PR_RESULT"
  else
    echo "Failed to create PR for $REPO (might already exist): $PR_RESULT"
  fi
}

# Loop through the repositories and add the workflow file via PR
MAX_JOBS=5
N=0
for REPO in $REPOS; do
  process_repo "$REPO" &
  ((N++))
  if [ $N -ge $MAX_JOBS ]; then
    wait
    N=0
  fi
done

wait
