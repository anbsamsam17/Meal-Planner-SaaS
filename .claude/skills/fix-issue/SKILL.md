---
name: fix-issue
description: "Fix a GitHub issue end-to-end: read the issue, find relevant code, implement the fix, write tests, and create a PR. Use when the user mentions: fix, bug, issue, ticket, error, regression."
argument-hint: "[issue-number]"
disable-model-invocation: true
allowed-tools: Bash(gh *) Bash(git *) Bash(make *) Read Grep Glob Edit Write
---

# Skill : Fix Issue — Presto (MealPlanner SaaS)

Fix GitHub issue: $ARGUMENTS

## Protocol

1. **Read the issue**: `gh issue view $ARGUMENTS` to get full details and labels
2. **Understand context**: Read `memory/project-context.md` and `memory/hindsight.md`
3. **Identify the layer**:
   - Label `frontend` → code dans `apps/web/src/`
   - Label `backend` → code dans `apps/api/src/`
   - Label `worker` → code dans `apps/worker/src/`
   - Label `db` → code dans `packages/db/src/`
4. **Find relevant code**: Search the codebase for files related to the issue
5. **Implement the fix**: Follow project conventions from `CLAUDE.md` and `.claude/rules/`
6. **Write/update tests**:
   - Backend → `pytest` dans `apps/api/tests/`
   - Frontend → `vitest` dans `apps/web/src/**/__tests__/`
7. **Validate**:
   - `make lint` — linting passes
   - `make test-api` ou `make test-web` — tests pass
8. **Create a PR**: `gh pr create` with description linking the issue

## Rules

- Fix the root cause, not the symptom
- Keep the fix minimal — don't refactor unrelated code
- Si le fix touche la DB → vérifier les policies RLS
- Si le fix touche Stripe → tester les webhooks
- Document the fix dans `memory/hindsight.md` si c'est une leçon réutilisable
