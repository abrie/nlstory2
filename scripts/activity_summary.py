import os
import requests
import argparse
from jinja2 import Environment, FileSystemLoader

GITHUB_API_URL = "https://api.github.com/graphql"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_issues_and_pull_requests(repository):
    query = """
    {
      repository(owner: "%s", name: "%s") {
        issues(first: 100, states: [OPEN, CLOSED]) {
          nodes {
            title
            createdAt
            timelineItems(itemTypes: CROSS_REFERENCED_EVENT) {
              nodes {
                ... on CrossReferencedEvent {
                  source {
                    ... on PullRequest {
                      title
                      createdAt
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

    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.post(GITHUB_API_URL, json={'query': query}, headers=headers)
    if response.status_code == 200:
        return response.json()['data']['repository']['issues']['nodes']
    else:
        raise Exception(f"Query failed to run by returning code of {response.status_code}. {query}")

def generate_summary(issues):
    summary = []
    for issue in issues:
        summary.append({
            'title': issue['title'],
            'createdAt': issue['createdAt'],
            'pullRequests': [
                {
                    'title': pr['source']['title'],
                    'createdAt': pr['source']['createdAt']
                } for pr in issue['timelineItems']['nodes']
            ]
        })
    summary.sort(key=lambda x: x['createdAt'])
    return summary

def render_html(summary, output_file):
    env = Environment(loader=FileSystemLoader('scripts/templates'))
    template = env.get_template('summary_template.html')
    with open(output_file, 'w') as f:
        f.write(template.render(summary=summary))

def main():
    parser = argparse.ArgumentParser(description='Generate a summary of significant activity from a GitHub repository.')
    parser.add_argument('--repository', required=True, help='GitHub repository in the format owner/repo')
    parser.add_argument('--output', required=True, help='Output HTML file')
    args = parser.parse_args()

    issues = get_issues_and_pull_requests(args.repository)
    summary = generate_summary(issues)
    render_html(summary, args.output)

if __name__ == "__main__":
    main()
