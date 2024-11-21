# nlstory2

## CLI Utility for Generating Summary of Significant Activity

This repository includes a CLI utility that generates a summary of significant activity from a Github repository using the Github GraphQL API and outputs it as an HTML file.

### Usage

To use the CLI utility, run the following command:

```sh
python scripts/generate_summary.py --repository <owner/repo> --output <output_file>
```

### Parameters

- `--repository`: The repository to fetch data from (e.g., owner/repo).
- `--output`: The output HTML file.

### Example

```sh
python scripts/generate_summary.py --repository abrie/nlstory2 --output summary.html
```

Make sure to set the `GITHUB_TOKEN` environment variable with your Github token before running the utility.

```sh
export GITHUB_TOKEN=your_github_token
```
