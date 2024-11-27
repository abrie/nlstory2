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


def query_github(query):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.post(GITHUB_API_URL, json={
                             "query": query}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(
            f"Query failed to run by returning code of {response.status_code}. {query}")


def render_template(prompt_events, commits_without_prs):
    env = Environment(loader=FileSystemLoader('scripts'))
    template = env.get_template('summary_template.html')
    return template.render(prompt_events=prompt_events, commits_without_prs=commits_without_prs)


def get_commits_without_prs():
    query = """
    {
        repository(owner: "abrie", name: "nl12") {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100) {
                            edges {
                                node {
                                    oid
                                    message
                                    committedDate
                                    associatedPullRequests(first: 1) {
                                        edges {
                                            node {
                                                number
                                            }
                                        }
                                    }
                                }
                            }
                            pageInfo {
                                hasNextPage
                                endCursor
                            }
                        }
                    }
                }
            }
        }
    }
    """
    commits_without_prs = []
    has_next_page = True
    end_cursor = None

    while has_next_page:
        paginated_query = query
        if end_cursor:
            paginated_query = query.replace("first: 100", f'first: 100, after: "{end_cursor}"')
        
        result = query_github(paginated_query)
        history = result["data"]["repository"]["defaultBranchRef"]["target"]["history"]
        
        for edge in history["edges"]:
            commit = edge["node"]
            if not commit["associatedPullRequests"]["edges"]:
                commits_without_prs.append({
                    "oid": commit["oid"],
                    "message": commit["message"],
                    "committedDate": commit["committedDate"]
                })
        
        has_next_page = history["pageInfo"]["hasNextPage"]
        end_cursor = history["pageInfo"]["endCursor"]

    return commits_without_prs


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
                            pageInfo {
                                hasNextPage
                                endCursor
                            }
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }
    """
    prompt_events = []
    has_next_page = True
    end_cursor = None

    while has_next_page:
        paginated_query = query
        if end_cursor:
            paginated_query = query.replace("first: 100", f'first: 100, after: "{end_cursor}"')
        
        result = query_github(paginated_query)
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
        
        has_next_page = issues["pageInfo"]["hasNextPage"]
        end_cursor = issues["pageInfo"]["endCursor"]

    prompt_events.sort(key=lambda x: x.timestamp)
    
    commits_without_prs = get_commits_without_prs()
    
    output = render_template(prompt_events, commits_without_prs)
    with open("index.html", "w") as f:
        f.write(output)


if __name__ == "__main__":
    main()
