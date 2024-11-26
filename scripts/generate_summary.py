import os
import requests
from jinja2 import Environment, FileSystemLoader

GITHUB_API_URL = "https://api.github.com/graphql"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def query_github(query):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.post(GITHUB_API_URL, json={
                             "query": query}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            f"Query failed to run by returning code of {response.status_code}. {query}")


def render_template(issues):
    env = Environment(loader=FileSystemLoader('scripts'))
    template = env.get_template('summary_template.html')
    return template.render(issues=issues)


def main(show_all_issues=True):
    query = """
    {
        repository(owner: "abrie", name: "nl12") {
            issues(first: 100) {
                edges {
                    node {
                        title
                        createdAt
                        url
                        body
                        timelineItems(itemTypes: CROSS_REFERENCED_EVENT, first: 100) {
                            edges {
                                node {
                                    ... on CrossReferencedEvent {
                                        source {
                                            ... on PullRequest {
                                                title
                                                createdAt
                                                url
                                                merged
                                                headRefName
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
    result = query_github(query)
    issues = []
    for edge in result["data"]["repository"]["issues"]["edges"]:
        issue = edge["node"]
        pull_requests = []
        for pr_edge in issue["timelineItems"]["edges"]:
            pr = pr_edge["node"]["source"]
            pull_requests.append({
                "createdAt": pr["createdAt"],
                "merged": pr["merged"],
                "branch": pr["headRefName"]
            })
        if show_all_issues or any(pr["merged"] for pr in pull_requests):
            issues.append({
                "title": issue["title"],
                "createdAt": issue["createdAt"],
                "url": issue["url"],
                "description": issue["body"],
                "pull_requests": pull_requests
            })
    issues.sort(key=lambda x: x["createdAt"])
    output = render_template(issues)
    with open("index.html", "w") as f:
        f.write(output)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a summary of issues and pull requests.")
    parser.add_argument("--show-all-issues", action="store_true", help="Show all issues, including those without merged PRs.")
    args = parser.parse_args()
    main(show_all_issues=args.show_all_issues)
