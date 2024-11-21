import argparse
import os
import requests
import jinja2

def get_github_data(repository):
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"
    }
    query = """
    query($owner: String!, $name: String!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        issues(first: 100, after: $cursor) {
          edges {
            node {
              title
              createdAt
              timelineItems(itemTypes: CROSS_REFERENCED_EVENT, first: 100) {
                edges {
                  node {
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
          pageInfo {
            endCursor
            hasNextPage
          }
        }
      }
    }
    """
    owner, name = repository.split('/')
    data = []
    cursor = None
    while True:
        variables = {"owner": owner, "name": name, "cursor": cursor}
        response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
        result = response.json()
        issues = result['data']['repository']['issues']['edges']
        for issue in issues:
            data.append(issue['node'])
        if not result['data']['repository']['issues']['pageInfo']['hasNextPage']:
            break
        cursor = result['data']['repository']['issues']['pageInfo']['endCursor']
    return data

def generate_summary(data):
    summary = []
    for issue in data:
        if 'pullRequest' not in issue:
            summary.append({
                'title': issue['title'],
                'createdAt': issue['createdAt'],
                'pullRequests': [
                    {
                        'title': pr['node']['source']['title'],
                        'createdAt': pr['node']['source']['createdAt']
                    }
                    for pr in issue['timelineItems']['edges']
                ]
            })
    summary.sort(key=lambda x: x['createdAt'])
    return summary

def create_html(summary, output_file):
    template_loader = jinja2.FileSystemLoader(searchpath="./scripts/templates")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("summary_template.html")
    output = template.render(summary=summary)
    with open(output_file, "w") as f:
        f.write(output)

def main():
    parser = argparse.ArgumentParser(description="Generate a summary of significant activity from a Github repository.")
    parser.add_argument("--repository", required=True, help="The repository to fetch data from (e.g., owner/repo).")
    parser.add_argument("--output", required=True, help="The output HTML file.")
    args = parser.parse_args()

    data = get_github_data(args.repository)
    summary = generate_summary(data)
    create_html(summary, args.output)

if __name__ == "__main__":
    main()
