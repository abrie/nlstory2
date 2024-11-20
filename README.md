# nlstory2

## CLI Utility for Generating Commit History HTML

This repository contains a CLI utility that generates an HTML page of all commits for a specified repository. The utility pulls the entire main trunk's commit history, determines if each commit came from a Pull Request, attaches related Issues and Pull Requests, and outputs the collected data in ascending chronological order using a Jinja template.

### Usage

To use the CLI utility, follow these steps:

1. Ensure you have Python installed on your system.
2. Set the `GITHUB_TOKEN` environment variable with your Github personal access token.
3. Run the following command:

```sh
python scripts/generate_commit_history.py --repository <owner/repo> --output <output_file>
```

Replace `<owner/repo>` with the repository you want to pull commit history from (e.g., `abrie/nlstory2`) and `<output_file>` with the desired output HTML file (e.g., `commit_history.html`).

### Example

```sh
python scripts/generate_commit_history.py --repository abrie/nlstory2 --output commit_history.html
```

This command will generate an HTML file named `commit_history.html` containing the commit history of the `abrie/nlstory2` repository.

### GITHUB_TOKEN

The `GITHUB_TOKEN` environment variable is required to authenticate with the Github GraphQL API. You can create a personal access token by following the instructions in the [Github documentation](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token).

Set the `GITHUB_TOKEN` environment variable in your terminal session before running the CLI utility:

```sh
export GITHUB_TOKEN=<your_personal_access_token>
```

Replace `<your_personal_access_token>` with the token you created.
