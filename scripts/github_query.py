import requests
import json
import os
import argparse

def get_issues(repository):
    url = 'https://api.github.com/graphql'
    token = os.getenv('GITHUB_TOKEN')
    headers = {'Authorization': f'bearer {token}'}
    query = """
    {
        repository(owner: "%s", name: "%s") {
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
    """ % tuple(repository.split('/'))
    response = requests.post(url, json={'query': query}, headers=headers)
    return response.json()

def write_output(data, output_file):
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Github GraphQL query utility')
    parser.add_argument('--repository', required=True, help='Repository in the format owner/name')
    parser.add_argument('--output', required=True, help='Output file')
    args = parser.parse_args()

    issues = get_issues(args.repository)
    write_output(issues, args.output)
