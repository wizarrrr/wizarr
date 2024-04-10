#!/bin/bash

# Fetch all tags from the remote repository
git fetch --tags

# Get the list of tags
tags=$(git tag -l)

# Iterate through each tag and retag with 'v' if it doesn't start with 'v'
for tag in $tags; do
    if [[ $tag == v* ]]; then
        echo "Tag $tag already starts with 'v', skipping."
    else
        new_tag="v$tag"
        git tag $new_tag $tag
        git tag -d $tag
        git push origin :refs/tags/$tag
        git push origin $new_tag
        echo "Retagged $tag as $new_tag"
    fi
done

# Push the updated tags to the remote repository
git push --tags