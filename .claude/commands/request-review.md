# /request-review Task

When this command is used, execute the following task:

# request-review

When the story is done and in the "Review" column, notify the team on the slack channel so they know your Pull request is ready to be reviewed.

## Prerequisites

- Story status must be "In Review"
- Developer has completed all tasks described in the story
- All automated tests are passing
- NEVER post anything to any slack channel besides the ones described in this document

## Request Review Process

1. **Checks before requesting review:**

   Do not proceed to next steps if any of the following are true:

   - If the PR does not exist on GitHub
   - If the PR already exists in the `workforce-internal` slack channel

2. **Prepare the PR to request review:**

   - Move the story to the "In review" column.
   - Make the PR ready to be reviewed on Github by removing it from Draft status

3. **Send the Pull request on Slack:**

   Post this message to the `workforce-internal` slack channel

```markdown
For review: [<quick summary of the PR contents](<link to the pull request in github>) - +<changes_added> -<changes_removed>
```

For example, this would become:
`For review: Adding a column to the Product table - +10 -2`

# Additional Information

## Slack Channel IDs

- #workforce-internal: C076EEUF6DP
