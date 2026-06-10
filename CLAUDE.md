# The Four Systems

Agentic SEO project: four cooperating agents (keyword research, content writing, onsite audit, refresh recommender) sharing a Business Value Score so commercial intent always beats raw search volume.

## Session start: check setup state (IMPORTANT)

At the start of every session, before doing anything else, run:

```bash
python3 scripts/check-setup.py --quiet
```

- **Exit 0 (setup complete):** say nothing about setup. Proceed with whatever the user asked.
- **Exit 1 (setup incomplete):** apply the protocol below. Do NOT ask "do you want to run the onboarding?". On an unconfigured project, onboarding IS the default behavior.

### Incomplete-setup protocol (zero fluff)

1. **If the user's message already contains setup material** (API keys, a site URL, money page URLs, file paths, pasted article examples), ingest it immediately: credentials go into `.mcp.json`, business answers into the right `context/` files. Never re-ask for anything they already gave. Then continue from the next missing item.
2. **Otherwise, start the onboarding directly** by invoking the `setup` skill. Your entire opening is at most 3 lines:
   - One line of status: "Setup incomplet: il reste N items." (mirror the user's language)
   - One line offering the fast path: "Tu peux tout me donner d'un coup (identifiants DataForSEO, URL du site, pages business, exemples d'articles) ou répondre question par question."
   - Then ask the FIRST missing item's question immediately (usually the DataForSEO credentials).
   No welcome speech, no recap of what the project is (the user just cloned it, they know), no enumeration of all missing items, no time estimate beyond a parenthetical if asked.
3. **If the user explicitly asks for something else**, do that instead, with a single one-line reminder that Systems 1 to 4 will not run until setup completes. Do not repeat the reminder in the same session.
4. The user can decline onboarding by saying so; respect that for the rest of the session.

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
