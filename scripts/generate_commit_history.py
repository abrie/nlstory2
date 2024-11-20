import os
import requests
import argparse
from jinja2 import Environment, FileSystemLoader

GITHUB_API_URL = "https://api.github.com/graphql"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_commit_history(repository):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    query = """
    query($owner: String!, $name: String!, $cursor: String) {
        repository(owner: $owner, name: $name) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor) {
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
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
                                                merged
                                                closed
                                                state
                                                timelineItems(itemTypes: [CROSS_REFERENCED_EVENT], first: 100) {
                                                    edges {
                                                        node {
                                                            ... on CrossReferencedEvent {
                                                                source {
                                                                    ... on Issue {
                                                                        number
                                                                        title
                                                                    }
                                                                    ... on PullRequest {
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
                            }
                        }
                    }
                }
            }
        }
    }
    """
    owner, name = repository.split("/")
    commit_history = []
    cursor = None

    while True:
        variables = {"owner": owner, "name": name, "cursor": cursor}
        response = requests.post(GITHUB_API_URL, json={"query": query, "variables": variables}, headers=headers)
        data = response.json()
        commits = data["data"]["repository"]["defaultBranchRef"]["target"]["history"]["edges"]
        commit_history.extend(commits)
        page_info = data["data"]["repository"]["defaultBranchRef"]["target"]["history"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

    return commit_history

def generate_html(commit_history, output_file):
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("index.html")
    output = template.render(commits=commit_history)
    with open(output_file, "w") as f:
        f.write(output)

def main():
    parser = argparse.ArgumentParser(description="Generate an HTML page of all commits for a repository.")
    parser.add_argument("--repository", required=True, help="The repository to pull commit history from (e.g., 'owner/repo').")
    parser.add_argument("--output", required=True, help="The output HTML file.")
    args = parser.parse_args()

    commit_history = get_commit_history(args.repository)
    generate_html(commit_history, args.output)

if __name__ == "__main__":
    main()
