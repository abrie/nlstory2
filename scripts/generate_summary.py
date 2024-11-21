import argparse
import os
import requests
import jinja2

def fetch_issues_and_prs(repository, token):
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}"}
    query = """
    {
      repository(owner: "%s", name: "%s") {
        issues(first: 100, orderBy: {field: CREATED_AT, direction: ASC}) {
          nodes {
            title
            url
            createdAt
            pullRequests(first: 10) {
              nodes {
                title
                url
                createdAt
              }
            }
          }
        }
      }
    }
    """ % tuple(repository.split('/'))
    response = requests.post(url, json={'query': query}, headers=headers)
    if response.status_code == 200:
        return response.json()['data']['repository']['issues']['nodes']
    else:
        raise Exception(f"Query failed to run by returning code of {response.status_code}. {query}")

def generate_html(issues, template_path, output_path):
    with open(template_path) as file_:
        template = jinja2.Template(file_.read())
    html_content = template.render(issues=issues)
    with open(output_path, 'w') as file_:
        file_.write(html_content)

def main():
    parser = argparse.ArgumentParser(description="Generate a summary of significant activity in a Github repository.")
    parser.add_argument('--repository', required=True, help='The repository to fetch data from (format: owner/repo).')
    parser.add_argument('--output', required=True, help='The output HTML file.')
    args = parser.parse_args()

    token = os.getenv('GITHUB_TOKEN')
    if not token:
        raise EnvironmentError("GITHUB_TOKEN environment variable not set.")

    issues = fetch_issues_and_prs(args.repository, token)
    generate_html(issues, 'scripts/template.html', args.output)

if __name__ == "__main__":
    main()
