import os
import requests
from jinja2 import Environment, FileSystemLoader

GITHUB_API_URL = "https://api.github.com/graphql"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


class PromptEvent:
    def __init__(self, issue, pull_requests):
        self.issue = issue
        self.pull_requests = pull_requests
        self.state = "Merged" if any(pr["merged"] for pr in pull_requests) else "Unmerged"
        self.timestamp = self.get_timestamp()

    def get_timestamp(self):
        if self.state == "Merged":
            merged_prs = [pr for pr in self.pull_requests if pr["merged"]]
            return min(pr["createdAt"] for pr in merged_prs)
        else:
            return self.issue["createdAt"]


class ManualEdit:
    def __init__(self, commit):
        self.commit = commit
        self.timestamp = commit["committedDate"]


def query_github(query):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.post(GITHUB_API_URL, json={
                             "query": query}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            f"Query failed to run by returning code of {response.status_code}. {query}")


def render_template(prompt_events):
    env = Environment(loader=FileSystemLoader('scripts'))
    template = env.get_template('summary_template.html')
    return template.render(prompt_events=prompt_events)


def main():
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
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100) {
                            edges {
                                node {
                                    committedDate
                                    message
                                    url
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
    prompt_events = []
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
        prompt_event = PromptEvent(issue, pull_requests)
        prompt_events.append(prompt_event)

    commits = result["data"]["repository"]["defaultBranchRef"]["target"]["history"]["edges"]
    for commit_edge in commits:
        commit = commit_edge["node"]
        if not any(pr["merged"] for pr in pull_requests):
            manual_edit = ManualEdit(commit)
            prompt_events.append(manual_edit)

    prompt_events.sort(key=lambda x: x.timestamp)
    output = render_template(prompt_events)
    with open("index.html", "w") as f:
        f.write(output)


if __name__ == "__main__":
    main()
