# /plan {what}

When this command is used make sure to use the planner agent.

# Instructions for the Planner Agent

First, check if there's a CONTEXT.md file and:

## If the CONTEXT.md file DOES exists

- Ask the agent to read the @CONTEXT.md file and come up with a plan to address it.
- DO NOT PROCEED If the @CONTEXT.md file says it had missing information about the ticket!

## If the CONTEXT.md file DOES NOT exists

- Create a plan for what's passed in as {what} parameter

# Output

- Write your solution to a PLAN.md file.
- Give a TLDR to the user about the plan
