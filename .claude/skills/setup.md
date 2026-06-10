---
name: setup
description: Guided first-run onboarding for The Four Systems. Checks what is missing (credentials, business context, seeds), then walks the user through it: DataForSEO + GSC keys into .mcp.json, site identity and money pages, editorial charter with good/bad article examples (URLs or PDFs analyzed automatically), remaining context files, seed keywords, final verification. Resumable at any point; state is whatever already exists on disk. Trigger when the user says "setup", "set up", "onboarding", "get started", "configure", "installation", "premiers pas", "configurer le projet", "demarrer", or when check-setup.py reports an incomplete setup at session start.
allowed-tools: Read, Write, Edit, Bash, WebFetch
---

# Setup (first-run onboarding wizard)

Walk a brand-new user from fresh clone to a fully configured project. Every phase is resumable: files already on disk are the resume state. Always re-run the doctor instead of assuming.

**Conduct this entire conversation in the user's language.** The repo ships in French and English. Mirror whatever the user speaks from the first message onward.

## Phase 0: Diagnose (always run first)

Run the doctor:

```bash
python3 scripts/check-setup.py --json
```

Parse the JSON output. Build a short human-readable summary: list what is complete with a checkmark, list what is missing with a bullet. Then give an honest time estimate:

- Full onboarding from zero: 30 to 45 minutes.
- Partial resume (some phases already done): shorter, tell them which phases remain.

Then jump immediately to the first incomplete phase. Never redo a phase whose files already exist. For each existing file, offer three options: **keep** (move on), **review** (read it together and confirm), **redo** (overwrite with fresh answers). Default to keep if the user does not object.

---

## Phase 1: Credentials

### 1a. DataForSEO

If `.mcp.json` is missing, create it from the example:

```bash
cp .mcp.json.example .mcp.json
```

Tell the user: "I need your DataForSEO credentials. These go only into `.mcp.json`, which is gitignored. I will never echo your password back, never copy it to any other file, and never commit it."

Ask for:
1. DataForSEO username (email address on the account).
2. DataForSEO password.

Write both directly into `.mcp.json` at the `DATAFORSEO_USERNAME` and `DATAFORSEO_PASSWORD` keys. Do not print the password back. Do not mention the password again after this step.

### 1b. Google Search Console (optional)

Explain: "GSC is only needed for System 4 (Refresh Recommender), which finds pages whose traffic is declining. You can skip it now and add it later."

Offer: **configure now** / **skip for now**.

If now: tell them to follow `docs/00-prerequisites.md` to install mcp-gsc, then ask for the local path to their mcp-gsc checkout. Update the `--directory` argument in the `gsc` server block in `.mcp.json`.

### 1c. Critical restart instruction

After any edit to `.mcp.json`, tell the user:

> "MCP servers are loaded once at session start. Type `/exit`, then run `claude` again in this folder, then say `setup` to resume. The doctor will detect that credentials are done and continue from Phase 2."

This restart is normal and expected. Do not try to work around it.

---

## Phase 2: Site identity and business goals

This phase produces `context/site-config.md`, `context/services.md`, and `context/audit-urls.txt`.

Ask the following questions explicitly and in this order. Push back on vague answers.

### 2a. Who is the site and what are its goals?

Ask for one specific paragraph covering: what the business is, who it serves, what makes it different, and what a "win" looks like (a lead, a sale, a signup, a phone call). If the answer is generic ("we help businesses succeed"), ask again and specify: dollars, percentages, named customer types, named technology. "We help businesses succeed" is not acceptable. "We sell a $49/month SEO dashboard to freelance consultants managing 5 to 20 client sites" is.

### 2b. What are the priority business pages (money pages)?

Collect 3 to 8 URLs with a one-line "what this page sells" for each. These are the pages that generate revenue or capture leads. If the user cannot name 3, ask what they would lose sleep over if those pages fell off Google.

### 2c. Locale and content type

- `target_country` and `target_language` (e.g. France / fr, United States / en). Required. DataForSEO calls pass this on every request.
- If multilingual: primary locale plus list of alternates.
- Default content type for new posts: `evergreen | software | news | ymyl | reference | commercial`. This drives staleness thresholds in System 4.

### 2d. Write the files

Follow the skeletons in `context-templates/*.example` as layout guides. Write three files:

**`context/site-config.md`** -- use the skeleton from context-bootstrapper Section A.

**`context/services.md`** -- put the money pages from 2b under a "Primary commercial URLs" section at the top (URL + one-line description). Below that, seed a short "What we sell" list from the conversation. Use the services skeleton from context-bootstrapper Section E for the rest.

**`context/audit-urls.txt`** -- one URL per line: the homepage plus the top 2 to 4 money pages from 2b.

Save each file immediately before moving on.

---

## Phase 3: Editorial charter with examples

This is the phase that separates generic AI content from content that sounds like the site. Be thorough.

### 3a. Voice

Ask: "How does your site write? Think about: formal or conversational, first or second person, sentence length, formatting habits (do you use lots of subheadings? bullet lists? bold callouts?), and any phrases or structures you actively ban."

This answer goes to `context/tone-of-voice.md`. Use the skeleton from context-bootstrapper Section C, including the hard default line: "Never use em dashes. Use colons, commas, parentheses, or separate sentences."

### 3b. Examples: good and bad articles

Ask: "Show me 2 to 5 examples of GOOD articles -- yours or competitors you admire -- and, if you have any, 1 to 3 BAD examples of content you would never want to produce."

Accept any mix of input formats:

- **URL**: fetch with WebFetch.
- **Local PDF**: the user gives a file path; read with the Read tool (it reads PDFs natively).
- **Local .md or .txt**: Read tool.
- **Local .docx**: tell the user Read cannot open docx directly. On macOS suggest `textutil -convert txt file.docx` as a quick converter, then share the .txt. Or paste the text directly into the conversation.

For each example, analyze:
- Structure: heading pattern, intro style, section lengths, closing move.
- Voice markers: person (first, second, third), register, recurring phrasings, sentence rhythm.
- Evidence style: does it cite data? examples? case studies? quotes?
- Formatting habits: lists, tables, bold usage, pull quotes.
- For good examples: what makes this worth replicating.
- For bad examples: exactly what the writer must not do, tied back to the user's goals.

### 3c. Synthesize into editorial-charter.md

Write `context/editorial-charter.md` with this exact skeleton:

```markdown
# Editorial charter (generated from examples)

## What a good article looks like here
- <pattern 1, concrete and checkable>
- <pattern 2>
...

## Anti-patterns (never produce these)
- <anti-pattern 1, concrete and checkable>
- <anti-pattern 2>
...

## Structural template observed in good examples
<typical heading flow, intro contract, section rhythm, closing move>

## Style DNA
<voice markers extracted from the good examples: person, sentence rhythm, lexical habits, recurring phrasings>

## Self-review rubric additions
The content writer must check the draft against each line below before declaring done:
- [ ] <checkable rule derived from the examples>
- [ ] <checkable rule>
...

## Sources analyzed
- GOOD: <url or filename> : <one-line takeaway>
- BAD: <url or filename> : <one-line takeaway>
```

Explain to the user: "The content writer reads this file when it exists and treats the anti-patterns as review failures. This charter extends the prompts without mutating them, so a future `git pull` to get upstream updates stays clean."

### 3d. Advanced option: prompt patching

At the end of Phase 3, offer this only if the user has a hard rule that directly contradicts the default methodology (example: they require a references section at the bottom, which the default prompt forbids).

Say: "If you have a rule that contradicts the default prompt logic, I can patch `prompts/content-writer.md` directly. Warning: local prompt edits may conflict with future upstream updates. Do you have any such rule, or does the charter cover everything?"

Only open the prompt file if they say yes and describe a specific contradiction.

---

## Phase 4: Remaining context files

Read `.claude/skills/context-bootstrapper.md`. Run the following sections from its Phase 3 interview in order:

- Section B: `context/audience.md`
- Section D: `context/experience-notes.md`
- Section F: `context/brand-guidelines.md`
- Section G: `context/competitors.md`
- Section H: `context/author.md`

For each file: if it already exists on disk, offer keep / review / redo before asking questions. If keeping, skip straight to the next file.

Follow context-bootstrapper's hard rules throughout this phase:
- No em dashes in any generated file.
- No fabrication: if the user has no answer, write "None to date" or `[TK: what to add here]`.
- Read before write: if a file exists, read it first and merge rather than overwrite.
- Save after each section.
- Push back on vague answers; use concrete specifics.

---

## Phase 5: Seeds and final verification

### 5a. Seed keywords

Ask: "What are 3 to 10 seed keywords aligned with your money pages? Think: what would a paying customer type into Google just before they buy?"

Replace the placeholder lines in `state/seed-keywords.txt` with one keyword per line. Do not leave the example placeholders.

### 5b. Final verification

Run the doctor again:

```bash
python3 scripts/check-setup.py
```

**If exit 0 (everything complete):**

Congratulate the user. Print the four commands they can run next:

```
Research keywords : say "research keywords for <seed>"
Write a post      : say "write a post about <topic>"
Run a site audit  : say "run an onsite audit"
Find pages to refresh : say "find pages to refresh"
```

Tell them where the dashboard lives: `output/keywords/dashboard.html`

If the `dfs-mcp` MCP server is active in this session (check whether DataForSEO tools are available), offer an optional smoke test: a single cheap `keyword_overview` call on the first seed keyword to confirm credentials work end to end. If the server is not loaded (because the user has not yet done the Phase 1 restart), remind them: "Restart claude in this folder once more to load the MCP server, then you can verify with a live call."

**If exit 1 (still incomplete):**

Show the remaining items. Do not end the session. Ask which item they want to tackle first.

### 5c. Closing note

Remind the user: "The more you fill in `context/experience-notes.md` with real customer stories, wins, and strong opinions over time, the more the articles will sound like you and less like a generic AI. That file is the highest-leverage thing you can keep enriching."

---

## Hard rules

- **Never echo a password after capture.** Write credentials to `.mcp.json` only. Do not repeat them, summarize them, or reference them in any other file.
- **No em dashes** in any generated file. Use colons, commas, parentheses, or split sentences. This rule is absolute.
- **No emojis** in generated files unless the user's tone-of-voice explicitly calls for them.
- **No fabrication.** Empty answers produce "None to date" or `[TK: ...]` markers. Never invent stats, customer names, credentials, or URLs.
- **One file per section, saved immediately.** An interrupted session loses nothing; the next run reads disk state.
- **Files on disk are the resume state.** Always re-run `check-setup.py` rather than assuming what is complete.
- **Language mirroring.** Conduct the full conversation in whatever language the user uses. Do not switch languages mid-session.
