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


def query_github(query, variables=None):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.post(GITHUB_API_URL, json={
                             "query": query, "variables": variables}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            f"Query failed to run by returning code of {response.status_code}. {query}")


def fetch_all_issues():
    query = """
    query($cursor: String) {
        repository(owner: "abrie", name: "nl12") {
            issues(first: 100, after: $cursor) {
                pageInfo {
                    endCursor
                    hasNextPage
                }
                edges {
                    node {
                        title
                        createdAt
                        url
                        body
                        timelineItems(itemTypes: CROSS_REFERENCED_EVENT, first: 100) {
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
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
    all_issues = []
    cursor = None
    while True:
        result = query_github(query, {"cursor": cursor})
        issues = result["data"]["repository"]["issues"]["edges"]
        all_issues.extend(issues)
        page_info = result["data"]["repository"]["issues"]["pageInfo"]
        if page_info["hasNextPage"]:
            cursor = page_info["endCursor"]
        else:
            break
    return all_issues


def fetch_all_timeline_items(issue):
    all_timeline_items = []
    cursor = None
    while True:
        result = query_github(issue["timelineItems"]["query"], {"cursor": cursor})
        timeline_items = result["data"]["repository"]["issue"]["timelineItems"]["edges"]
        all_timeline_items.extend(timeline_items)
        page_info = result["data"]["repository"]["issue"]["timelineItems"]["pageInfo"]
        if page_info["hasNextPage"]:
            cursor = page_info["endCursor"]
        else:
            break
    return all_timeline_items


def render_template(prompt_events):
    env = Environment(loader=FileSystemLoader('scripts'))
    template = env.get_template('summary_template.html')
    return template.render(prompt_events=prompt_events)


def main():
    issues = fetch_all_issues()
    prompt_events = []
    for edge in issues:
        issue = edge["node"]
        timeline_items = fetch_all_timeline_items(issue)
        pull_requests = []
        for pr_edge in timeline_items:
            pr = pr_edge["node"]["source"]
            pull_requests.append({
                "createdAt": pr["createdAt"],
                "merged": pr["merged"],
                "branch": pr["headRefName"]
            })
        prompt_event = PromptEvent(issue, pull_requests)
        prompt_events.append(prompt_event)
    prompt_events.sort(key=lambda x: x.timestamp)
    output = render_template(prompt_events)
    with open("index.html", "w") as f:
        f.write(output)


if __name__ == "__main__":
    main()
