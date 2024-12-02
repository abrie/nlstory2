import os
import requests
from jinja2 import Environment, FileSystemLoader
import subprocess
import shutil
import tempfile

GITHUB_API_URL = "https://api.github.com/graphql"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


class PromptEvent:
    def __init__(self, issue, pull_requests):
        self.issue = issue
        self.pull_requests = pull_requests
        self.state = "Merged" if any(pr["merged"]
                                     for pr in pull_requests) else "Unmerged"
        self.timestamp = self.get_timestamp()
        self.headline = issue['titleHTML']
        self.body = issue['bodyHTML']
        self.oid = None
        self.abbreviatedOid = None
        for pr in pull_requests:
            if pr["oid"]:
                self.oid = pr["oid"]
                self.abbreviatedOid = pr["abbreviatedOid"]
                break

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
        self.oid = commit.get('oid')
        self.abbreviatedOid = commit.get('abbreviatedOid')

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
                                    oid
                                    abbreviatedOid
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
                    "url": commit["url"],
                    "oid": commit["oid"],
                    "abbreviatedOid": commit["abbreviatedOid"]
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
                                                mergeCommit {
                                                    oid
                                                    abbreviatedOid
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
                    "branch": pr["headRefName"],
                    "oid": pr["mergeCommit"]["oid"] if pr["merged"] else None,
                    "abbreviatedOid": pr["mergeCommit"]["abbreviatedOid"] if pr["merged"] else None
                })
            prompt_event = PromptEvent(issue, pull_requests)
            prompt_events.append(prompt_event)
        print(f"Processed a page of issues, cursor: {cursor}")
        if not issues["pageInfo"]["hasNextPage"]:
            break
        cursor = issues["pageInfo"]["endCursor"]
    prompt_events.sort(key=lambda x: x.timestamp)
    return prompt_events


def build_project_for_event(event, repo_path, builds_path):
    event_path = os.path.join(builds_path, event.abbreviatedOid)
    if not os.path.exists(event_path):
        os.makedirs(event_path)

    try:
        # Check out the associated oid
        subprocess.run(["git", "checkout", event.oid], cwd=repo_path, check=True)

        # Remove all files and folders that are not part of the source tree
        for item in os.listdir(repo_path):
            if item not in ["src", "public", "package.json", "tsconfig.json", "vite.config.js"]:
                item_path = os.path.join(repo_path, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)

        # Install dependencies
        subprocess.run(["yarn", "install"], cwd=repo_path, check=True)

        # Build the project
        subprocess.run(["npx", "vite", "build"], cwd=repo_path, check=True)

        # Move the contents of the 'dist' folder into the event folder
        dist_path = os.path.join(repo_path, "dist")
        for item in os.listdir(dist_path):
            shutil.move(os.path.join(dist_path, item), event_path)
    except subprocess.CalledProcessError as e:
        print(f"Error occurred during build for event {event.abbreviatedOid}: {e}")
    except Exception as e:
        print(f"Unexpected error occurred during build for event {event.abbreviatedOid}: {e}")


def main():
    prompt_events = query_issues_and_prs()
    main_trunk_commits = get_main_trunk_commits()

    events = prompt_events + main_trunk_commits
    events.sort(key=lambda x: x.timestamp if isinstance(
        x, PromptEvent) else x.timestamp)

    # Clone the abrie/nl12 repository into a temporary location
    repo_path = tempfile.mkdtemp()
    subprocess.run(["git", "clone", "https://github.com/abrie/nl12.git", repo_path], check=True)

    # Create a 'builds' folder in the local directory
    builds_path = os.path.abspath("builds")
    if not os.path.exists(builds_path):
        os.makedirs(builds_path)

    # Build the project for each significant event
    for event in events:
        if isinstance(event, PromptEvent) and event.state == "Merged":
            build_project_for_event(event, repo_path, builds_path)
        elif isinstance(event, CommitEvent):
            build_project_for_event(event, repo_path, builds_path)

    print("Generating template...")
    output = render_template(events)
    output_file_path = os.path.abspath("index.html")
    with open(output_file_path, "w") as f:
        f.write(output)
    print(
        f"Summary page generated successfully. Output file: {output_file_path}")


if __name__ == "__main__":
    main()
