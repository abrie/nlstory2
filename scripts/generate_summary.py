import requests
import os
import argparse
import jinja2
import json

def fetch_issues(owner, repo):
    url = 'https://api.github.com/graphql'
    headers = {
        'Authorization': f'bearer {os.getenv("GITHUB_TOKEN")}'
    }
    query = """
    query($owner: String!, $repo: String!, $cursor: String) {
        repository(owner: $owner, name: $repo) {
            issues(first: 100, after: $cursor) {
                pageInfo {
                    endCursor
                    hasNextPage
                }
                edges {
                    node {
                        __typename
                        title
                        createdAt
                        timelineItems(first: 100) {
                            nodes {
                                ... on CrossReferencedEvent {
                                    source {
                                        ... on PullRequest {
                                            __typename
                                            merged
                                            number
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
    }
    """
    issues = []
    cursor = None
    while True:
        variables = {
            'owner': owner,
            'repo': repo,
            'cursor': cursor
        }
        response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
        if response.status_code == 200:
            data = response.json()
            issues.extend(data['data']['repository']['issues']['edges'])
            if data['data']['repository']['issues']['pageInfo']['hasNextPage']:
                cursor = data['data']['repository']['issues']['pageInfo']['endCursor']
            else:
                break
        else:
            raise Exception(f"Query failed to run by returning code of {response.status_code}. {query}")
    return issues, query

def generate_summary(issues):
    summary = []
    for issue in issues:
        issue_node = issue['node']
        summary.append({
            'type': issue_node['__typename'],
            'title': issue_node['title'],
            'createdAt': issue_node['createdAt']
        })
        for event in issue_node['timelineItems']['nodes']:
            if 'source' in event and event['source']['__typename'] == 'PullRequest' and event['source']['merged']:
                summary.append({
                    'type': event['source']['__typename'],
                    'title': event['source']['title'],
                    'createdAt': event['source']['createdAt']
                })
    summary.sort(key=lambda x: x['createdAt'])
    return summary

def render_html(summary, output_file):
    template_loader = jinja2.FileSystemLoader(searchpath="./scripts")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("template.html")
    output = template.render(summary=summary)
    with open(output_file, 'w') as f:
        f.write(output)

def output_json(data, output_file):
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=4)

def output_query_json(query, output_file):
    with open(output_file, 'w') as f:
        json.dump({"query": query}, f, indent=4)

def main():
    parser = argparse.ArgumentParser(description='Generate a summary of significant activity from a repository.')
    parser.add_argument('--repository', required=True, help='The repository to fetch data from (format: owner/repo).')
    parser.add_argument('--output', required=True, help='The output HTML file.')
    parser.add_argument('--json', help='The output JSON file.')
    parser.add_argument('--query-json', help='The output JSON file for the GraphQL query.')
    args = parser.parse_args()

    owner, repo = args.repository.split('/')
    issues, query = fetch_issues(owner, repo)
    summary = generate_summary(issues)
    render_html(summary, args.output)

    if args.json:
        output_json(issues, args.json)
    
    if args.query_json:
        output_query_json(query, args.query_json)

if __name__ == "__main__":
    main()
