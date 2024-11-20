import argparse
import requests
import os
import json

def get_github_data(repository):
    url = "https://api.github.com/graphql"
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    query = """
    {
      repository(owner: "%s", name: "%s") {
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 100) {
                edges {
                  node {
                    message
                    oid
                    author {
                      name
                      email
                      date
                    }
                    committer {
                      name
                      email
                      date
                    }
                    associatedPullRequests(first: 5) {
                      edges {
                        node {
                          title
                          number
                          state
                          merged
                          mergeCommit {
                            oid
                          }
                          author {
                            login
                          }
                          body
                          comments(first: 5) {
                            edges {
                              node {
                                body
                                author {
                                  login
                                }
                              }
                            }
                          }
                          reviews(first: 5) {
                            edges {
                              node {
                                body
                                author {
                                  login
                                }
                              }
                            }
                          }
                          labels(first: 5) {
                            edges {
                              node {
                                name
                              }
                            }
                          }
                          milestone {
                            title
                          }
                          assignees(first: 5) {
                            edges {
                              node {
                                login
                              }
                            }
                          }
                          projectCards(first: 5) {
                            edges {
                              node {
                                note
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
    """ % tuple(repository.split('/'))
    response = requests.post(url, json={'query': query}, headers=headers)
    return response.json()

def generate_summary(data):
    summary = []
    commits = data['data']['repository']['defaultBranchRef']['target']['history']['edges']
    for commit in commits:
        commit_node = commit['node']
        commit_summary = f"Commit: {commit_node['message']} by {commit_node['author']['name']} on {commit_node['author']['date']}"
        if commit_node['associatedPullRequests']['edges']:
            pr = commit_node['associatedPullRequests']['edges'][0]['node']
            pr_summary = f"PR: {pr['title']} by {pr['author']['login']} - {pr['state']}"
            commit_summary += f" | {pr_summary}"
            if pr['merged']:
                issue_summary = f"Issue: {pr['body']}"
                commit_summary += f" | {issue_summary}"
                unmerged_prs = [pr_edge['node'] for pr_edge in commit_node['associatedPullRequests']['edges'] if not pr_edge['node']['merged']]
                if unmerged_prs:
                    unmerged_prs_summary = "Unmerged PRs: " + ", ".join([f"{pr['title']} by {pr['author']['login']}" for pr in unmerged_prs])
                    commit_summary += f" | {unmerged_prs_summary}"
        summary.append(commit_summary)
    return summary

def main():
    parser = argparse.ArgumentParser(description="Generate a summary of significant activity for a given repository.")
    parser.add_argument("--repository", required=True, help="The repository to analyze (format: owner/repo).")
    parser.add_argument("--output", required=True, help="The output file to save the summary.")
    args = parser.parse_args()

    data = get_github_data(args.repository)
    summary = generate_summary(data)

    with open(args.output, 'w') as output_file:
        for line in summary:
            output_file.write(line + "\n")

if __name__ == "__main__":
    main()
