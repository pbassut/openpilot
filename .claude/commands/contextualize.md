# /contextualize {url_or_story_id}

When this command is used make sure to use the context-provider agent

# Instructions for the context-provider agent

- DO NOT proceed if you don't have access to a Jira Story or any information that's critical for context building.
- Build context on the url/story id given to you as a parameter. That might be a GitHub PR, a jira story, a notion doc, a slack conversation, etc.
- If it's a Jira story and it:
  - has an epic, make sure to look at the epic as well as the Figma links attached if any;
  - has a Figma URL, make sure to read the components used in the Figma file since they should directly map to what exists in the Castle library;

Write your plan to a CONTEXT.md file

# Input

- The input might be given as a Jira Story ID in the format SC-XXXXX or even XXXXX without the SC prefix. In which case you should prepend `https://secureframe.atlassian.net/browse/<STORY_ID>` to it.
- Use the Jira getJiraIssue tool to get the story information

# Output

- Give a TLDR to the user about the gathered context.
