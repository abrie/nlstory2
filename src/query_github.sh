#!/bin/bash

# Check if GITHUB_TOKEN is set
if [ -z "$GITHUB_TOKEN" ]; then
  echo "Error: GITHUB_TOKEN is not set."
  exit 1
fi

# Perform the GraphQL query using curl
response=$(curl -s -H "Authorization: bearer $GITHUB_TOKEN" -X POST -d @query.json https://api.github.com/graphql)

# Output the response as JSON
echo "$response" | jq .
