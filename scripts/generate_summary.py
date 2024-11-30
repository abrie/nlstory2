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
                commits.append({
                    "committedDate": commit["committedDate"],
                    "messageHeadlineHTML": commit["messageHeadlineHTML"],
                    "messageBodyHTML": commit["messageBodyHTML"],
                    "url": commit["url"]
                })
        print(f"Processed a page of commits, cursor: {cursor}")
        if not history["pageInfo"]["hasNextPage"]:
            break
        cursor = history["pageInfo"]["endCursor"]
    commits.sort(key=lambda x: x["committedDate"])
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
                        title
                        createdAt
                        url
                        bodyHTML
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


def clone_repository():
    temp_dir = tempfile.mkdtemp()
    repo_url = "https://github.com/abrie/nl12.git"
    subprocess.run(["git", "clone", repo_url, temp_dir], check=True)
    return temp_dir


def checkout_commit(repo_dir, commit_id):
    subprocess.run(["git", "checkout", commit_id], cwd=repo_dir, check=True)


def build_project(repo_dir):
    subprocess.run(["yarn", "install"], cwd=repo_dir, check=True)
    subprocess.run(["npx", "vite", "build"], cwd=repo_dir, check=True)


def copy_dist_folder(repo_dir, commit_id):
    dist_dir = os.path.join(repo_dir, "dist")
    builds_dir = os.path.abspath("builds")
    os.makedirs(builds_dir, exist_ok=True)
    target_dir = os.path.join(builds_dir, commit_id)
    shutil.copytree(dist_dir, target_dir)


def clean_up(repo_dir):
    shutil.rmtree(os.path.join(repo_dir, "node_modules"))
    shutil.rmtree(os.path.join(repo_dir, "dist"))
    subprocess.run(["git", "checkout", "main"], cwd=repo_dir, check=True)


def main():
    prompt_events = query_issues_and_prs()
    main_trunk_commits = get_main_trunk_commits()
    
    events = prompt_events + main_trunk_commits
    events.sort(key=lambda x: x.timestamp if isinstance(x, PromptEvent) else x["committedDate"])
    
    print("Cloning repository...")
    repo_dir = clone_repository()
    
    for event in events:
        commit_id = event.issue["url"].split("/")[-1] if isinstance(event, PromptEvent) else event["url"].split("/")[-1]
        print(f"Processing commit {commit_id}...")
        checkout_commit(repo_dir, commit_id)
        build_project(repo_dir)
        copy_dist_folder(repo_dir, commit_id)
        clean_up(repo_dir)
    
    print("Removing cloned repository...")
    shutil.rmtree(repo_dir)
    
    print("Generating template...")
    output = render_template(events)
    output_file_path = os.path.abspath("index.html")
    with open(output_file_path, "w") as f:
        f.write(output)
    print(f"Summary page generated successfully. Output file: {output_file_path}")


if __name__ == "__main__":
    main()
