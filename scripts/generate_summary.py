import os
import requests
from jinja2 import Environment, FileSystemLoader
import subprocess
import shutil
import tempfile
import argparse

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


def build_project(oid, abbreviatedOid):
    repo_dir = "nl12_repo"
    if not os.path.exists(repo_dir):
        subprocess.run(
            ["git", "clone", "https://github.com/abrie/nl12.git", repo_dir], check=True)
    temp_dir = tempfile.mkdtemp()
    try:
        shutil.copytree(repo_dir, temp_dir, dirs_exist_ok=True)
        subprocess.run(["git", "switch", "--detach", oid],
                       cwd=temp_dir, check=True)
        subprocess.run(["git", "clean", "-fdx"], cwd=temp_dir, check=True)
        subprocess.run(["yarn", "install", "--silent"],
                       cwd=temp_dir, check=True)
        result = subprocess.run(
            ["npx", "vite", "build", "--base", "./", "--logLevel", "silent"], cwd=temp_dir)
        if result.returncode != 0:
            print(f"Build failed for {abbreviatedOid}")
            return
        build_dir = os.path.join("builds", abbreviatedOid)
        os.makedirs(build_dir, exist_ok=True)
        dist_dir = os.path.join(temp_dir, "dist")
        for item in os.listdir(dist_dir):
            s = os.path.join(dist_dir, item)
            d = os.path.join(build_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
    finally:
        shutil.rmtree(temp_dir)


def main():
    parser = argparse.ArgumentParser(description="Generate summary")
    parser.add_argument("--build-significant-steps", action="store_true",
                        help="Toggle building of significant steps")
    args = parser.parse_args()

    prompt_events = query_issues_and_prs()
    main_trunk_commits = get_main_trunk_commits()

    events = prompt_events + main_trunk_commits
    events.sort(key=lambda x: x.timestamp if isinstance(
        x, PromptEvent) else x.timestamp)

    if args.build_significant_steps:
        os.makedirs("builds", exist_ok=True)
        for event in events:
            if isinstance(event, PromptEvent) and event.state == "Merged":
                build_project(event.oid, event.abbreviatedOid)
            elif isinstance(event, CommitEvent):
                build_project(event.oid, event.abbreviatedOid)

    print("Generating template...")
    output = render_template(events)
    output_file_path = os.path.abspath("index.html")
    with open(output_file_path, "w") as f:
        f.write(output)
    print(
        f"Summary page generated successfully. Output file: {output_file_path}")

    if os.path.exists("nl12_repo"):
        shutil.rmtree("nl12_repo")


if __name__ == "__main__":
    main()
