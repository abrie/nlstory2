import os
import requests
import json

def query_github():
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    headers = {
        "Authorization": f"Bearer {github_token}"
    }

    query = """
    {
        repository(owner: "abrie", name: "nl12") {
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
    """

    response = requests.post(
        'https://api.github.com/graphql',
        json={'query': query},
        headers=headers
    )

    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        raise Exception(f"Query failed to run by returning code of {response.status_code}. {response.text}")

if __name__ == "__main__":
    query_github()
