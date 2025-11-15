# /ci

Check if there's a PLAN.md file present. If not, stop and tell the user. Only proceed if the PLAN.md file is present.
DO NOT read the file yourself. Only the developer agent can read it.

Then, use the developer agent to:

- Create a branch off of origin/main if not specified otherwise;
- Follow your "Story Development Workflow" for the PLAN.md;
- Before committing your code, make sure to delete CONTEXT.md(if it exists) and PLAN.md files - KEEP them in the git history for later debugging
