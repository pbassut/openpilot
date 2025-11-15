# /address-requests {Pull Request}

When this command is invoked, ask the developer agent to run the following

# address-requests

People will comment on your PR with review suggestions, you need to read their requests and either implement it or tell the user why you didn't implement it.

If the PR link is not given to you, figure it out by looking at the context or the current branch name.

When this command is used, execute the following tasks:

## Address Requests

1. **Look up all reviews done on the Pull Request:**

- Don't implement reviews requests that:
  - Are already marked as resolved(see the #tricks section on how to get this)
  - Were done in outdated code(see the #tricks section on how to get this)
  - Don't have any reaction or a negative one like ❌, 🙅, ⚔️, etc.
- Implement any review request that has a thumbsup(👍).
- For reviews with the eyes reaction(👀), give the user a explanation of why the reviewer might be right or wrong. NEVER RESPOND DIRECTLY TO THE GITHUB THREAD.

2. **Implement:**

- Implement the changes by following this flow:
  1. Focus on a single review request
  2. Immplement the change request in the request
  3. Push the change to the Pull Request
  4. Mark only that review request as done (See #tricks section below on how to do this)
  5. Repeat from step #1 until you either marked all requests as done or provided a "won't do" explanation.
- If you done every single change a person has requested, make sure to re-request review from the person if they haven't approved the pull request. If they approved the PR, no action is needed. Note: Don't request review for the PR author
- Reviewers expect the code on the same Pull Request. So, push the code to the Pull Request's branch. DON'T EVER CREATE A NEW BRANCH

3. **Wrap up:**

- Push the changes to the remote branch
- List the review comments you addressed and tell the user a reason why you didn't address others.

# Tricks

## Getting all unresolved comments

Use GitHub's GraphQL API via gh api graphql with the resolveReviewThread mutation:

```
gh api graphql -f query='
query {
  repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: PULL_REQUEST_NUMBER) {
      reviewThreads(last: 10) {
        nodes {
          isOutdated
          isResolved
          comments(last: 50) {
            nodes {
              body
              author {
                login
              }
            }
          }
        }
      }
    }
  }
}'  | jq '.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false and .isOutdated == false)'
```

## Marking PR Review Comments as Resolved

Use GitHub's GraphQL API via gh api graphql with the resolveReviewThread mutation:

### Single thread

```
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {threadId: "PRRT_kwDODnWqHM5Wyg3S"}) {
    thread { id }
  }
}'
```

### Multiple threads in one request

```
gh api graphql -f query='
mutation ResolveMultiple {
  r1: resolveReviewThread(input: {threadId: "PRRT_kwDODnWqHM5Wyc9l"}) {
    thread { id }
  }
  r2: resolveReviewThread(input: {threadId: "PRRT_kwDODnWqHM5Wyg6N"}) {
    thread { id }
  }
}'
```

### Fetching channels from slack

Use channel_id to refer to a channel using the following list:

- workforce-internal - C076EEUF6DP

### Key steps:

1. Get thread IDs first using a query to list review threads
2. Use resolveReviewThread mutation with each thread ID
3. Can batch multiple resolutions in one GraphQL request using aliases (r1, r2, etc.)
4. Output what you have addressed, with either why you addressed it that way or why you won't address it.
