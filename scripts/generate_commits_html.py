import os
import sys
import requests
import jinja2
import argparse

def get_commits(repository, token):
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}
    query = """
    query($owner: String!, $name: String!, $cursor: String) {
        repository(owner: $owner, name: $name) {
            ref(qualifiedName: "main") {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor) {
                            edges {
                                node {
                                    oid
                                    message
                                    committedDate
                                    associatedPullRequests(first: 1) {
                                        edges {
                                            node {
                                                number
                                                title
                                                body
                                                url
                                                merged
                                                mergedAt
                                                closingIssuesReferences(first: 10) {
                                                    edges {
                                                        node {
                                                            number
                                                            title
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
        variables = {"owner": owner, "name": name, "cursor": cursor}
        response = requests.post(url, json={"query": query, "variables": variables}, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Query failed to run by returning code of {response.status_code}. {query}")

        result = response.json()
        history = result["data"]["repository"]["ref"]["target"]["history"]
        for edge in history["edges"]:
            commit = edge["node"]
            commits.append(commit)

        if not history["pageInfo"]["hasNextPage"]:
            break
        cursor = history["pageInfo"]["endCursor"]

    return commits

def get_pull_request(commit):
    if commit["associatedPullRequests"]["edges"]:
        return commit["associatedPullRequests"]["edges"][0]["node"]
    return None

def get_issues(pull_request):
    issues = []
    if pull_request and pull_request["closingIssuesReferences"]["edges"]:
        for edge in pull_request["closingIssuesReferences"]["edges"]:
            issues.append(edge["node"])
    return issues

def generate_html(commits, template_path, output_path):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath="./"))
    template = env.get_template(template_path)
    html_content = template.render(commits=commits)
    with open(output_path, "w") as f:
        f.write(html_content)

def main():
    parser = argparse.ArgumentParser(description="Generate HTML page of all commits from a repository")
    parser.add_argument("--repository", required=True, help="Repository in the format 'owner/name'")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    args = parser.parse_args()

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set")
        sys.exit(1)

    commits = get_commits(args.repository, token)
    for commit in commits:
        commit["pull_request"] = get_pull_request(commit)
        if commit["pull_request"]:
            commit["issues"] = get_issues(commit["pull_request"])

    generate_html(commits, "scripts/template.html", args.output)

if __name__ == "__main__":
    main()
