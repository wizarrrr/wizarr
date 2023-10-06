#!/bin/bash

# Current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Convert Swagger JSON to Markdown using swagger-markdown
npx swagger-markdown -i $DIR/../swagger.json -o $DIR/../docs/contribute/api.md