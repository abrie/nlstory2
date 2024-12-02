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
        self.headline = issue['titleHTML']
        self.body = issue['bodyHTML']

    def get_timestamp(self):
        if self.state == "Merged":
            merged_prs = [pr for pr in self.pull_requests if pr["merged"]]
            return min(pr["createdAt"] for pr in merged_prs)
        else:
            return self.issue["createdAt"]


class CommitEvent:
    def __init__(self, commit):
        self.commit = commit
        self.timestamp = self.get_timestamp()
        self.commit_hash = self.get_commit_hash()
        self.headline = commit['messageHeadlineHTML']
        self.body = commit['messageBodyHTML']

    def get_timestamp(self):
        return self.commit["committedDate"]

    def get_commit_hash(self):
        return self.commit["url"].split("/")[-1]


def query_github(query, variables=None):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.post(GITHUB_API_URL, json={
                             "query": query, "variables": variables}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            f"Query failed to run by returning code of {response.status_code}. {query}")


def render_template(events):
    env = Environment(loader=FileSystemLoader('scripts'))
    template = env.get_template('summary_template.html')
    return template.render(events=events)


def get_main_trunk_commits():
    print("Querying GitHub API for main trunk commits...")
    query = """
    query($cursor: String) {
        repository(owner: "abrie", name: "nl12") {
            ref(qualifiedName: "refs/heads/main") {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor) {
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                            edges {
                                node {
                                    committedDate
                                    messageHeadlineHTML
                                    messageBodyHTML
                                    url
                                    associatedPullRequests(first: 1) {
                                        totalCount
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
    cursor = None
    commits = []
    while True:
        result = query_github(query, {"cursor": cursor})
        history = result["data"]["repository"]["ref"]["target"]["history"]
        for edge in history["edges"]:
            commit = edge["node"]
            if commit["associatedPullRequests"]["totalCount"] == 0:
                commits.append(CommitEvent({
                    "committedDate": commit["committedDate"],
                    "messageHeadlineHTML": commit["messageHeadlineHTML"],
                    "messageBodyHTML": commit["messageBodyHTML"],
                    "url": commit["url"]
                }))
        print(f"Processed a page of commits, cursor: {cursor}")
        if not history["pageInfo"]["hasNextPage"]:
            break
        cursor = history["pageInfo"]["endCursor"]
    commits.sort(key=lambda x: x.timestamp)
    return commits


def query_issues_and_prs():
    print("Querying GitHub API for issues...")
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
                        createdAt
                        url
                        bodyHTML
                        titleHTML
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
    cursor = None
    prompt_events = []
    while True:
        result = query_github(query, {"cursor": cursor})
        issues = result["data"]["repository"]["issues"]
        for edge in issues["edges"]:
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
        print(f"Processed a page of issues, cursor: {cursor}")
        if not issues["pageInfo"]["hasNextPage"]:
            break
        cursor = issues["pageInfo"]["endCursor"]
    prompt_events.sort(key=lambda x: x.timestamp)
    return prompt_events


def main():
    prompt_events = query_issues_and_prs()
    main_trunk_commits = get_main_trunk_commits()
    
    events = prompt_events + main_trunk_commits
    events.sort(key=lambda x: x.timestamp if isinstance(x, PromptEvent) else x.timestamp)
    
    print("Generating template...")
    output = render_template(events)
    output_file_path = os.path.abspath("index.html")
    with open(output_file_path, "w") as f:
        f.write(output)
    print(f"Summary page generated successfully. Output file: {output_file_path}")


if __name__ == "__main__":
    main()
