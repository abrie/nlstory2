import argparse
import os
import requests
from jinja2 import Environment, FileSystemLoader

def get_commits(repository, token):
    url = 'https://api.github.com/graphql'
    headers = {'Authorization': f'bearer {token}'}
    query = """
    query($owner: String!, $name: String!, $cursor: String) {
        repository(owner: $owner, name: $name) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor) {
                            edges {
                                node {
                                    oid
                                    message
                                    author {
                                        name
                                        email
                                        date
                                    }
                                    associatedPullRequests(first: 1) {
                                        edges {
                                            node {
                                                number
                                                title
                                                body
                                                merged
                                                url
                                                closingIssuesReferences(first: 1) {
                                                    edges {
                                                        node {
                                                            number
                                                            title
                                                            body
                                                            url
                                                        }
                                                    }
                                                }
                                                referencedIssues(first: 1) {
                                                    edges {
                                                        node {
                                                            number
                                                            title
                                                            body
                                                            url
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                }
            }
        }
    }
    """
    owner, name = repository.split('/')
    commits = []
    cursor = None

    while True:
        variables = {'owner': owner, 'name': name, 'cursor': cursor}
        response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
        data = response.json()
        history = data['data']['repository']['defaultBranchRef']['target']['history']
        for edge in history['edges']:
            commit = edge['node']
            commits.append(commit)
        if not history['pageInfo']['hasNextPage']:
            break
        cursor = history['pageInfo']['endCursor']

    return commits

def main():
    parser = argparse.ArgumentParser(description='Generate an HTML page of all commits from a repository.')
    parser.add_argument('--repository', required=True, help='The repository to pull commits from (e.g., owner/repo).')
    parser.add_argument('--output', required=True, help='The output HTML file.')
    args = parser.parse_args()

    token = os.getenv('GITHUB_TOKEN')
    if not token:
        raise ValueError('GITHUB_TOKEN environment variable not set.')

    commits = get_commits(args.repository, token)

    # Sort commits chronologically in ascending order
    commits.sort(key=lambda x: x['author']['date'])

    env = Environment(loader=FileSystemLoader('scripts'))
    template = env.get_template('template.html')
    output = template.render(repository=args.repository, commits=commits)

    with open(args.output, 'w') as f:
        f.write(output)

if __name__ == '__main__':
    main()
