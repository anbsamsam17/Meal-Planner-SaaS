---
name: commit
description: "Stage and commit changes with a conventional commit message. Use when the user mentions: commit, save, checkpoint, stage changes."
disable-model-invocation: true
allowed-tools: Bash(git *) Bash(make lint) Bash(make format)
---

# Skill : Commit — Presto

Stage and commit the current changes following Conventional Commits.

## Steps

1. Run `git status` to see what changed
2. Run `git diff --stat` to understand the scope
3. Run `make format` to auto-format
4. Run `make lint` to check — fix any issues
5. Stage relevant files with `git add` (specific files, NOT `git add .`)
6. Write a commit message following Conventional Commits:
   - `feat:` — new feature
   - `fix:` — bug fix
   - `docs:` — documentation only
   - `refactor:` — code change that neither fixes nor adds
   - `test:` — adding or fixing tests
   - `chore:` — maintenance, dependencies, CI
   - `style:` — formatting, no logic change
7. Commit with `git commit -m "type(scope): concise description"`

## Scopes recommandés pour Presto

- `api` — Backend FastAPI
- `web` — Frontend Next.js
- `worker` — Celery worker
- `db` — Database models/migrations
- `stripe` — Payment integration
- `ci` — CI/CD pipeline
- `infra` — Infrastructure

## Rules

- Never commit `.env`, `.env.local`, credentials, or secrets
- Never use `git add .` or `git add -A` — stage specific files
- One commit per logical change
- Message in imperative mood: "add feature" not "added feature"
- pre-commit hooks will run automatically (ruff, prettier, gitleaks)
