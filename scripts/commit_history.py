import argparse
import os
import requests

def get_commits(repository, token):
    url = 'https://api.github.com/graphql'
    headers = {'Authorization': f'bearer {token}'}
    query = """
    query($owner: String!, $name: String!, $cursor: String) {
      repository(owner: $owner, name: $name) {
        ref(qualifiedName: "main") {
          target {
            ... on Commit {
              history(first: 100, after: $cursor) {
                edges {
                  node {
                    oid
                    message
                    author {
                      name
                      email
                      date
                    }
                    associatedPullRequests(first: 1) {
                      edges {
                        node {
                          number
                          title
                          body
                          merged
                          url
                          author {
                            login
                          }
                          closingIssuesReferences(first: 1) {
                            edges {
                              node {
                                number
                                title
                                body
                                url
                                author {
                                  login
                                }
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
                pageInfo {
                  endCursor
                  hasNextPage
                }
              }
            }
          }
        }
      }
    }
    """
    owner, name = repository.split('/')
    cursor = None
    commits = []

    while True:
        variables = {'owner': owner, 'name': name, 'cursor': cursor}
        response = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Query failed to run by returning code of {response.status_code}. {query}")
        result = response.json()
        commits.extend(result['data']['repository']['ref']['target']['history']['edges'])
        page_info = result['data']['repository']['ref']['target']['history']['pageInfo']
        if not page_info['hasNextPage']:
            break
        cursor = page_info['endCursor']

    return commits

def generate_html(commits, output_file):
    with open('index.html', 'r') as file:
        template = file.read()

    commit_entries = []
    for commit in commits:
        commit_data = commit['node']
        pr_data = commit_data['associatedPullRequests']['edges'][0]['node'] if commit_data['associatedPullRequests']['edges'] else None
        issue_data = pr_data['closingIssuesReferences']['edges'][0]['node'] if pr_data and pr_data['closingIssuesReferences']['edges'] else None

        commit_entry = f"""
        <div class="commit">
            <p><strong>Commit:</strong> {commit_data['oid']}</p>
            <p><strong>Message:</strong> {commit_data['message']}</p>
            <p><strong>Author:</strong> {commit_data['author']['name']} ({commit_data['author']['email']})</p>
            <p><strong>Date:</strong> {commit_data['author']['date']}</p>
        """
        if pr_data:
            commit_entry += f"""
            <div class="pull-request">
                <p><strong>Pull Request:</strong> <a href="{pr_data['url']}">#{pr_data['number']}</a> - {pr_data['title']}</p>
                <p><strong>Author:</strong> {pr_data['author']['login']}</p>
                <p><strong>Merged:</strong> {'Yes' if pr_data['merged'] else 'No'}</p>
                <p><strong>Body:</strong> {pr_data['body']}</p>
            </div>
            """
        if issue_data:
            commit_entry += f"""
            <div class="issue">
                <p><strong>Issue:</strong> <a href="{issue_data['url']}">#{issue_data['number']}</a> - {issue_data['title']}</p>
                <p><strong>Author:</strong> {issue_data['author']['login']}</p>
                <p><strong>Body:</strong> {issue_data['body']}</p>
            </div>
            """
        commit_entry += "</div>"
        commit_entries.append(commit_entry)

    html_content = template.replace("<!-- commit_data_placeholder -->", "\n".join(commit_entries))

    with open(output_file, 'w') as file:
        file.write(html_content)

def main():
    parser = argparse.ArgumentParser(description='Generate an HTML page of all commits from a specified repository.')
    parser.add_argument('--repository', required=True, help='The repository to pull commit history from (e.g., owner/repo).')
    parser.add_argument('--output', required=True, help='The output HTML file.')
    args = parser.parse_args()

    token = os.getenv('GITHUB_TOKEN')
    if not token:
        raise Exception('GITHUB_TOKEN environment variable not set.')

    commits = get_commits(args.repository, token)
    generate_html(commits, args.output)

if __name__ == '__main__':
    main()
