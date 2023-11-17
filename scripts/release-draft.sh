#!/bin/bash

# Set your GitHub repository details
USERNAME="wizarrrr"
REPO="wizarr"

# Get your GitHub Personal Access Token
# Make sure it has the "repo" scope
CURRENT_DIR=$(pwd)
TOKEN=$(cat $CURRENT_DIR/scripts/github_token.txt)

# Fetch all releases (including drafts) using the GitHub API
releases=$(curl -s -H "Authorization: token $TOKEN" "https://api.github.com/repos/$USERNAME/$REPO/releases?per_page=100")

# Delete all releases that are drafts
for row in $(echo "${releases}" | jq -r '.[] | @base64'); do
    _jq() {
        echo ${row} | base64 --decode | jq -r ${1}
    }
    
    if [ $(_jq '.draft') == true ]; then
        id=$(_jq '.id')
        echo "Deleting release with id $id and tag $(_jq '.tag_name')"
        curl -X DELETE -H "Authorization: token $TOKEN" "https://api.github.com/repos/$USERNAME/$REPO/releases/$id"
    fi
done