import argparse
import os
import requests
import jinja2

def get_commits(repository):
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}"
    }
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
                    committedDate
                    associatedPullRequests(first: 1) {
                      edges {
                        node {
                          title
                          number
                          merged
                          mergeCommit {
                            oid
                          }
                          associatedIssues(first: 1) {
                            edges {
                              node {
                                title
                                number
                                state
                                url
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

def generate_html(commits, output_file):
    template_loader = jinja2.FileSystemLoader(searchpath="scripts/templates")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("summary_template.html")
    output = template.render(commits=commits)
    with open(output_file, "w") as f:
        f.write(output)

def main():
    parser = argparse.ArgumentParser(description="Generate a summary of significant activity from a repository.")
    parser.add_argument("--repository", required=True, help="The repository to fetch data from (format: owner/repo).")
    parser.add_argument("--output", required=True, help="The output HTML file.")
    args = parser.parse_args()

    commits = get_commits(args.repository)
    generate_html(commits, args.output)

if __name__ == "__main__":
    main()
