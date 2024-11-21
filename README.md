# nlstory2

## CLI Utility for Generating Repository Summary

This repository includes a CLI utility that generates an HTML summary of significant activity from a repository using the Github GraphQL API.

### Usage

To use the CLI utility, run the following command:

```
python scripts/generate_summary.py --repository <owner/repo> --output <output_file>
```

### Parameters

- `--repository`: The repository to fetch data from (format: owner/repo).
- `--output`: The output HTML file.

### Example

```
python scripts/generate_summary.py --repository abrie/nlstory2 --output summary.html
```

### Authentication

The utility requires the GITHUB_TOKEN environment variable for authentication. Make sure to set this variable before running the utility.

```
export GITHUB_TOKEN=<your_github_token>
```
