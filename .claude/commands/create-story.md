# /create-story {context}

When this command is used make sure to use the project-owner agent

# Instructions for the project-owner agent

- First check if you have access to Jira. If not, stop IMMEDIATELY and tell the user you can't proceed without Jira access.
- If no context is provided, research the current branch changes and create a Jira ticket based on the information you find.
- Make the story description short but still containing all relevant information for a developer to complete the story.

# Input

- Context on the Jira Story to create

# Output

- Give a TLDR to the user about the gathered context.
