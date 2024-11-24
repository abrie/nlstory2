import { request, gql } from 'graphql-request';

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;

const query = gql`
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
`;

const endpoint = 'https://api.github.com/graphql';

const headers = {
  Authorization: `Bearer ${GITHUB_TOKEN}`,
};

request(endpoint, query, {}, headers)
  .then((data) => console.log(JSON.stringify(data, null, 2)))
  .catch((error) => console.error(error));
