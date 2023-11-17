#!/bin/bash

# Set your GitHub repository details
USERNAME="wizarrrr"
REPO="wizarr"

# Get your GitHub Personal Access Token
# Make sure it has the "repo" scope
CURRENT_DIR=$(pwd)
TOKEN=$(cat $CURRENT_DIR/scripts/github_token.txt)

# Set the workflow ID
WORKFLOW_ID="39941505"

# Get all the runs for the workflow ID
WORKFLOW_RUNS_URL="https://api.github.com/repos/$USERNAME/$REPO/actions/workflows/$WORKFLOW_ID/runs?per_page=1000"
WORKFLOW_RUNS=$(curl -s -H "Authorization: token $TOKEN" $WORKFLOW_RUNS_URL)

# List all the run IDs
RUN_IDS=$(echo $WORKFLOW_RUNS | jq -r '.workflow_runs[].id')

I=0

for run_id in $RUN_IDS; do
    echo "$I: Deleting run with ID $run_id"
    curl -X DELETE -H "Authorization: token $TOKEN" \
    "https://api.github.com/repos/$USERNAME/$REPO/actions/runs/$run_id"
    I=$((I+1))
done