#!/bin/bash

if [ -z "$GITHUB_TOKEN" ]; then
  echo "GITHUB_TOKEN is not set"
  exit 1
fi

QUERY=$(cat query.graphql)

curl -H "Authorization: bearer $GITHUB_TOKEN" -X POST -d "{\"query\": \"$QUERY\"}" https://api.github.com/graphql | jq .
