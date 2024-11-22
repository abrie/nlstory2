# nlstory2

## CLI Utility for Generating Summary of Significant Activity

This repository contains a CLI utility that generates a summary of significant activity from a repository and outputs it as an HTML file.

### Usage

To use the CLI utility, run the following command:

```sh
python scripts/generate_summary.py --repository <owner/repo> --output <output_file>
```

To output the query as JSON, use the `--json` parameter:

```sh
python scripts/generate_summary.py --repository <owner/repo> --output <output_file> --json <json_output_file>
```

### Example

```sh
python scripts/generate_summary.py --repository abrie/nlstory2 --output summary.html
```

### Requirements

- Python 3.x
- `requests` library
- `jinja2` library
- GITHUB_TOKEN environment variable for authentication

### Installation

To install the required libraries, run:

```sh
pip install requests jinja2
```

### Setting the GITHUB_TOKEN

Make sure to set the GITHUB_TOKEN environment variable before running the utility. You can do this by running:

```sh
export GITHUB_TOKEN=<your_github_token>
```
