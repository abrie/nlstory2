# nlstory2

## Summary Generator CLI Utility

This repository includes a CLI utility that generates a summary of significant activity from a GitHub repository using the GitHub GraphQL API and outputs it as an HTML file.

### Usage

To use the summary generator, run the following command:

```sh
python scripts/summary_generator.py --repository <owner/repo> --output <output_file>
```

### Parameters

- `--repository`: The repository to generate the summary from (e.g., `owner/repo`).
- `--output`: The output HTML file.

### Example

```sh
python scripts/summary_generator.py --repository abrie/nlstory2 --output summary.html
```

This will generate a summary of significant activity from the `abrie/nlstory2` repository and save it to `summary.html`.

### Requirements

- Python 3.x
- `requests` library
- `jinja2` library

### Installation

To install the required libraries, run:

```sh
pip install requests jinja2
```

### Environment Variables

The script uses the `GITHUB_TOKEN` environment variable for authentication with the GitHub GraphQL API. Make sure to set this environment variable before running the script.

```sh
export GITHUB_TOKEN=<your_github_token>
```
