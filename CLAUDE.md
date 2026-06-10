# The Four Systems

Agentic SEO project: four cooperating agents (keyword research, content writing, onsite audit, refresh recommender) sharing a Business Value Score so commercial intent always beats raw search volume.

## Session start: check setup state (IMPORTANT)

At the start of every session, before doing anything else, run:

```bash
python3 scripts/check-setup.py --quiet
```

- **Exit 1 (setup incomplete):** the project is not configured yet. Greet the user, tell them the setup is incomplete, and offer to run the guided onboarding right away: "Your project is not fully configured yet. Want me to walk you through the setup? It takes 30 to 45 minutes the first time and you can stop and resume anytime. Just say yes or type 'setup'." If they accept, invoke the `setup` skill. If they ask for something else first, help them, but remind them that Systems 1 to 4 will not run correctly until setup is complete.
- **Exit 0 (setup complete):** say nothing about setup. Proceed with whatever the user asked.

The doctor is cheap and silent with `--quiet`; never skip this check.

## What runs what

- The four agent skills live in `.claude/skills/` (keyword-researcher, content-writer, onsite-audit, refresh-recommender), plus `setup` (onboarding) and `context-bootstrapper` (business interview).
- Agent methodology lives in `prompts/`. The Business Value Score spec at `prompts/_business-value-scoring.md` is read by all four agents.
- Business context lives in `context/` (gitignored, per-user). If a required context file is missing, do not improvise its content: tell the user to run `setup`.
- Runtime state lives in `state/`, deliverables in `output/`, human-readable reports in `reports/`.

## Project conventions

- Never use em dashes in any generated file. Use colons, commas, parentheses, or separate sentences.
- No emojis in generated files unless the user's tone-of-voice file explicitly allows them.
- Never fabricate stats, customer stories, citations, or credentials. Missing data is "None to date" or a `[TK: ...]` marker.
- Credentials belong in `.mcp.json` only (gitignored). Never echo a password back, never copy credentials anywhere else, never commit them.
- After any edit to `.mcp.json`, MCP servers need a session restart to load. Tell the user to `/exit` and rerun `claude`.
- `state/` JSON files are owned by specific systems (see `docs/06-architecture.md`). Respect ownership: System 2 never edits `keyword-bank.json`, System 4 layer 2 only writes `refresh-queue.json` and `serp-snapshots/`.
- Update the dashboard after any state change: `python3 scripts/render-html-report.py`.

## Useful entry points

- Project map: `STRUCTURE.md`
- Setup guide: `docs/00-prerequisites.md`
- Architecture (who reads/writes what): `docs/06-architecture.md`
- Business Value Score explained: `docs/05-business-value-scoring.md`
