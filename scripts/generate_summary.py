import argparse
import os
import requests
import jinja2
from datetime import datetime

def fetch_issues_and_pulls(repository):
    issues = []
    pulls = []
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_TOKEN")}'
    }
    page = 1
    while True:
        response = requests.get(f'https://api.github.com/repos/{repository}/issues', headers=headers, params={'state': 'all', 'page': page})
        if response.status_code != 200:
            break
        data = response.json()
        if not data:
            break
        for item in data:
            if 'pull_request' in item:
                pulls.append(item)
            else:
                issues.append(item)
        page += 1
    return issues, pulls

def generate_summary(issues, pulls):
    summary = []
    for issue in issues:
        issue_summary = {
            'title': issue['title'],
            'created_at': issue['created_at'],
            'pull_requests': []
        }
        for pull in pulls:
            if any(ref['issue_url'] == issue['url'] for ref in pull.get('timeline', [])):
                issue_summary['pull_requests'].append({
                    'title': pull['title'],
                    'created_at': pull['created_at']
                })
        summary.append(issue_summary)
    summary.sort(key=lambda x: datetime.strptime(x['created_at'], '%Y-%m-%dT%H:%M:%SZ'))
    return summary

def generate_html(summary, output_file):
    template_loader = jinja2.FileSystemLoader(searchpath="scripts/")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("summary_template.html")
    output = template.render(summary=summary)
    with open(output_file, 'w') as f:
        f.write(output)

def main():
    parser = argparse.ArgumentParser(description='Generate a summary of significant activity from a repository.')
    parser.add_argument('--repository', required=True, help='The repository to fetch data from.')
    parser.add_argument('--output', required=True, help='The output HTML file.')
    args = parser.parse_args()

    issues, pulls = fetch_issues_and_pulls(args.repository)
    summary = generate_summary(issues, pulls)
    generate_html(summary, args.output)

if __name__ == "__main__":
    main()
