import os
import requests

def query_github():
    url = "https://api.github.com/graphql"
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    query = """
    {
      repository(owner: "abrie", name: "nl12") {
        issues(first: 100) {
          edges {
            node {
              __typename
              title
              timelineItems(first: 100) {
                nodes {
                  ... on CrossReferencedEvent {
                    source {
                      ... on PullRequest {
                        __typename
                        merged
                        number
                        title
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
    """
    response = requests.post(url, json={'query': query}, headers=headers)
    print(response.json())

if __name__ == "__main__":
    query_github()
