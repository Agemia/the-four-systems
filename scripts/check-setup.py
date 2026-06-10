#!/usr/bin/env python3
"""
check-setup.py -- Setup doctor for "The Four Systems" agentic SEO project.

Detects missing credentials, business context files, and configuration so that
an onboarding skill can resume exactly where the user left off.

Exit codes:
  0  Setup complete (all blocking checks passed).
  1  Setup incomplete (at least one blocking item present).
  2  Unexpected error during the check itself.
"""
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OK, BLOCK, WARN, INFO = "ok", "blocking", "warning", "info"
SEED_PLACEHOLDERS = {"example seed keyword", "another example seed"}
CONTEXT_FILES = [
    "site-config.md", "audience.md", "tone-of-voice.md", "experience-notes.md",
    "services.md", "brand-guidelines.md", "competitors.md", "author.md", "audit-urls.txt",
]
SETUP_HINT = "Run the setup skill (say 'setup' in Claude Code) or copy from context-templates/"

def r(cid, status, label, hint=""):
    return {"id": cid, "status": status, "label": label, "hint": hint}

def _load_mcp():
    p = ROOT / ".mcp.json"
    if not p.exists():
        return None, "missing"
    try:
        return json.loads(p.read_text("utf-8")), None
    except json.JSONDecodeError as e:
        return None, str(e)

def run_checks():
    mcp, merr = _load_mcp()
    out = []

    # --- Tooling ---
    # 3.10+ is the documented target; 3.9 demonstrably runs every script (lazy
    # annotations via __future__), so it only warns. Below 3.9 blocks.
    if sys.version_info >= (3, 10):
        out.append(r("python_version", OK, "Python >= 3.10"))
    elif sys.version_info >= (3, 9):
        out.append(r("python_version", WARN, f"Python {sys.version_info.major}.{sys.version_info.minor} detected (3.10+ recommended)",
                     "The scripts run on 3.9, but upgrade when convenient: https://www.python.org/downloads/"))
    else:
        out.append(r("python_version", BLOCK, f"Python {sys.version_info.major}.{sys.version_info.minor} detected",
                     "Upgrade to Python 3.10 or later: https://www.python.org/downloads/"))
    out.append(r("node_available", OK, "Node / npx found") if (shutil.which("node") or shutil.which("npx"))
               else r("node_available", WARN, "Node / npx not found",
                      "Install Node 18+: https://nodejs.org or brew install node"))

    # --- Credentials ---
    out.append(r("mcp_json_exists", OK, ".mcp.json present") if (ROOT / ".mcp.json").exists()
               else r("mcp_json_exists", BLOCK, ".mcp.json missing", "cp .mcp.json.example .mcp.json"))

    if merr and merr != "missing":
        out.append(r("dataforseo_creds", BLOCK, ".mcp.json has invalid JSON", "Fix the JSON syntax in .mcp.json"))
    elif mcp is not None:
        CHINT = "Edit .mcp.json with your DataForSEO credentials (dashboard > API Access)"
        try:
            env = mcp["mcpServers"]["dfs-mcp"]["env"]
            bad = (not env.get("DATAFORSEO_USERNAME") or env["DATAFORSEO_USERNAME"] == "you@example.com"
                   or not env.get("DATAFORSEO_PASSWORD") or env["DATAFORSEO_PASSWORD"] == "your-dataforseo-password")
        except (KeyError, TypeError):
            bad = True
        out.append(r("dataforseo_creds", BLOCK, "DataForSEO credentials not filled in", CHINT) if bad
                   else r("dataforseo_creds", OK, "DataForSEO credentials set"))
        try:
            args = mcp["mcpServers"]["gsc"]["args"]
            if any("/path/to" in str(a) for a in args):
                out.append(r("gsc_mcp_path", WARN, "GSC server path still contains placeholder",
                             "Update the gsc server --directory in .mcp.json to your local mcp-gsc "
                             "checkout (see docs/00-prerequisites.md). Optional until you run System 4."))
            else:
                out.append(r("gsc_mcp_path", OK, "GSC server path configured"))
        except (KeyError, TypeError):
            pass

    slp = ROOT / ".claude" / "settings.local.json"
    out.append(r("settings_local", OK, ".claude/settings.local.json present") if slp.exists()
               else r("settings_local", WARN, ".claude/settings.local.json missing",
                      "cp .claude/settings.local.json.example .claude/settings.local.json (avoids permission prompts)"))

    # --- Business context ---
    for fname in CONTEXT_FILES:
        cid = "context_" + Path(fname).stem.replace("-", "_").replace(".", "_")
        p = ROOT / "context" / fname
        out.append(r(cid, OK, f"context/{fname}") if p.exists()
                   else r(cid, BLOCK, f"context/{fname} missing", SETUP_HINT))

    sc = ROOT / "context" / "site-config.md"
    if sc.exists():
        txt = sc.read_text("utf-8", errors="replace").lower()
        missing = [f for f in ("target_country", "target_language") if f not in txt]
        out.append(r("locale_defined", BLOCK, f"Locale fields missing: {', '.join(missing)}",
                     "Add a Locale section to context/site-config.md (target_country + "
                     "target_language); every DataForSEO call needs it.") if missing
                   else r("locale_defined", OK, "target_country + target_language defined"))

    ec = ROOT / "context" / "editorial-charter.md"
    out.append(r("editorial_charter", OK, "context/editorial-charter.md present") if ec.exists()
               else r("editorial_charter", INFO, "context/editorial-charter.md absent (optional)",
                      "Optional: provide good/bad article examples during setup to generate "
                      "context/editorial-charter.md."))

    # --- Seeds ---
    skp = ROOT / "state" / "seed-keywords.txt"
    if skp.exists():
        real = [l.strip() for l in skp.read_text("utf-8", errors="replace").splitlines()
                if l.strip() and not l.strip().startswith("#") and l.strip().lower() not in SEED_PLACEHOLDERS]
        out.append(r("seed_keywords", OK, f"seed-keywords.txt has {len(real)} real seed(s)") if real
                   else r("seed_keywords", BLOCK, "seed-keywords.txt contains only placeholder entries",
                          "Add 3 to 10 real seed keywords to state/seed-keywords.txt, one per line."))
    else:
        out.append(r("seed_keywords", BLOCK, "state/seed-keywords.txt missing",
                     "Add 3 to 10 real seed keywords to state/seed-keywords.txt, one per line."))
    return out

# --- Output ---
SECTIONS = {
    "python_version": "Tooling", "node_available": "Tooling",
    "mcp_json_exists": "Credentials", "dataforseo_creds": "Credentials",
    "gsc_mcp_path": "Credentials", "settings_local": "Credentials",
    "locale_defined": "Business context", "editorial_charter": "Business context",
    "seed_keywords": "Seeds",
}
MARKERS = {OK: "[OK]", BLOCK: "[MISSING]", WARN: "[WARN]", INFO: "[INFO]"}

def _sec(item):
    return SECTIONS.get(item["id"], "Business context" if item["id"].startswith("context_") else "Other")

def print_human(results):
    for sec in ("Tooling", "Credentials", "Business context", "Seeds"):
        items = [x for x in results if _sec(x) == sec]
        if not items:
            continue
        print(f"\n{sec}\n{'-' * len(sec)}")
        for x in items:
            line = f"  {MARKERS[x['status']]} {x['label']}"
            if x["hint"] and x["status"] != OK:
                line += f": {x['hint']}"
            print(line)
    print()
    blocking = [x for x in results if x["status"] == BLOCK]
    warnings = [x for x in results if x["status"] == WARN]
    if not blocking:
        example = "your seed"
        try:
            for raw in (ROOT / "state" / "seed-keywords.txt").read_text("utf-8").splitlines():
                l = raw.strip()
                if l and not l.startswith("#") and l.lower() not in SEED_PLACEHOLDERS:
                    example = l; break
        except OSError:
            pass
        print(f"Setup complete. All systems ready. Try: research keywords for {example}")
    else:
        print(f"Setup incomplete: {len(blocking)} blocking item(s), {len(warnings)} warning(s).")
        print(f"Next step: {blocking[0]['hint']}")
        print("Tip: open Claude Code in this folder and say \"setup\" to run the guided onboarding.")

def print_json_out(results):
    print(json.dumps({
        "complete": not any(x["status"] == BLOCK for x in results),
        "blocking": [{"id": x["id"], "hint": x["hint"]} for x in results if x["status"] == BLOCK],
        "warnings": [{"id": x["id"], "hint": x["hint"]} for x in results if x["status"] == WARN],
        "info":     [{"id": x["id"], "hint": x["hint"]} for x in results if x["status"] == INFO],
    }, indent=2))

def main():
    p = argparse.ArgumentParser(description="Setup doctor for The Four Systems SEO project.")
    p.add_argument("--json", action="store_true")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()
    try:
        results = run_checks()
    except Exception as exc:
        print(f"check-setup: unexpected error: {exc}", file=sys.stderr)
        sys.exit(2)
    if not args.quiet:
        print_json_out(results) if args.json else print_human(results)
    sys.exit(0 if not any(x["status"] == BLOCK for x in results) else 1)

if __name__ == "__main__":
    main()
