# /present {resource}

CRITICAL: Before running this command, make sure the branch has the format SC-XXXXX-<description-of-changes>. If it doesn't, stop and ask the user if they want to proceed creating a PR that has the wrong format. If the user asks you to skip this check, do so.

When this command is used, make sure to use the presenter agent.

Create a Pull Request with the given {resource}.
{resource} here might be:

- A pull request link;
- A local branch

# **Output Format:**

## Pull Request Creation

This is what you will inform back to the user about the pull request you created:

- Link on github
- Title
- Branch
- Number of files changes
- Amount of changes(Format: +N -M)

## Editing Pull Requests

- Modified Pull Request link on GitHub
