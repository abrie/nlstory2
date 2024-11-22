#!/bin/bash

# Function to display usage
usage() {
    echo "Usage: $0 --repository owner/name --output output_file"
    exit 1
}

# Parse CLI parameters
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --repository) REPOSITORY="$2"; shift ;;
        --output) OUTPUT="$2"; shift ;;
        *) usage ;;
    esac
    shift
done

# Check if required parameters are provided
if [ -z "$REPOSITORY" ] || [ -z "$OUTPUT" ]; then
    usage
fi

# Set the Github API URL and token
URL="https://api.github.com/graphql"
TOKEN="$GITHUB_TOKEN"

# Define the GraphQL query
QUERY=$(cat <<EOF
{
    repository(owner: "${REPOSITORY%/*}", name: "${REPOSITORY#*/}") {
        issues(first: 100) {
            edges {
                node {
                    __typename
                    title
                    timelineItems(first: 100) {
                        nodes {
                            ... on CrossReferencedEvent {
                                source {
                                    ... on PullRequest {
                                        __typename
                                        merged
                                        number
                                        title
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
EOF
)

# Make the API request and parse the response
RESPONSE=$(curl -s -H "Authorization: bearer $TOKEN" -X POST -d "{\"query\": \"$QUERY\"}" $URL)
echo $RESPONSE | jq '.' > "$OUTPUT"
