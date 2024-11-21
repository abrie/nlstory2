import os
import requests
import argparse
from jinja2 import Environment, FileSystemLoader

GITHUB_API_URL = "https://api.github.com/graphql"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_issues_and_pull_requests(repository):
    query = """
    query($owner: String!, $name: String!) {
        repository(owner: $owner, name: $name) {
            issues(first: 100) {
                edges {
                    node {
                        title
                        createdAt
                        url
                        timelineItems(itemTypes: CROSS_REFERENCED_EVENT, first: 100) {
                            edges {
                                node {
                                    ... on CrossReferencedEvent {
                                        source {
                                            ... on PullRequest {
                                                title
                                                createdAt
                                                url
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
    }
    """
    owner, name = repository.split('/')
    issues = []

    response = requests.post(
        GITHUB_API_URL,
        json={'query': query, 'variables': {'owner': owner, 'name': name}},
        headers={'Authorization': f'bearer {GITHUB_TOKEN}'}
    )
    data = response.json()
    issues.extend(data['data']['repository']['issues']['edges'])

    return issues

def generate_summary(issues):
    summary = []
    for issue in issues:
        summary.append({
            'title': issue['node']['title'],
            'createdAt': issue['node']['createdAt'],
            'url': issue['node']['url']
        })
        for event in issue['node']['timelineItems']['edges']:
            if 'source' in event['node'] and 'title' in event['node']['source']:
                summary.append({
                    'title': event['node']['source']['title'],
                    'createdAt': event['node']['source']['createdAt'],
                    'url': event['node']['source']['url']
                })
    summary.sort(key=lambda x: x['createdAt'])
    return summary

def render_html(summary, output_file):
    env = Environment(loader=FileSystemLoader('scripts'))
    template = env.get_template('template.html')
    with open(output_file, 'w') as f:
        f.write(template.render(summary=summary))

def main():
    parser = argparse.ArgumentParser(description='Generate a summary of significant activity from a repository.')
    parser.add_argument('--repository', required=True, help='The repository to generate the summary from (e.g., owner/repo).')
    parser.add_argument('--output', required=True, help='The output HTML file.')
    args = parser.parse_args()

    issues = get_issues_and_pull_requests(args.repository)
    summary = generate_summary(issues)
    render_html(summary, args.output)

if __name__ == '__main__':
    main()
