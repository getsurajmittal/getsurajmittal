#!/usr/bin/env python3
"""
Rebuilds the "Featured Projects" block in README.md straight from the GitHub API.

Any repo you create, rename, describe or push to shows up automatically the next
time this runs — no manual editing of the README ever again.

Run locally:   GITHUB_TOKEN=ghp_xxx python3 scripts/update_projects.py
In Actions:    handled by .github/workflows/readme-autoupdate.yml

Exit codes:  0 = fine (changed or not)   1 = something went wrong, message on stderr
"""

import json
import os
import sys
import urllib.error
import urllib.request

USER = os.environ.get("GH_USERNAME", "getsurajmittal")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = os.environ.get("README_PATH", "README.md")

CARD_COUNT = int(os.environ.get("CARD_COUNT", "4"))    # pinned-style cards (keep even)
TABLE_COUNT = int(os.environ.get("TABLE_COUNT", "6"))  # rows in the details table

EXCLUDE = {n.strip() for n in os.environ.get("EXCLUDE_REPOS", USER).split(",") if n.strip()}

START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"


def log(msg):
    print(msg, flush=True)


def die(msg):
    print(f"::error::{msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def api(path, optional=False):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-readme-updater",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = f"GitHub API {e.code} on {path}"
        if e.code == 403:
            detail += " (rate limited — is GITHUB_TOKEN set on the step?)"
        elif e.code == 404:
            detail += f" (does the user '{USER}' exist?)"
        if optional:
            log(f"  ! {detail} — skipping")
            return None
        die(detail)
    except Exception as e:  # network blip, DNS, timeout
        if optional:
            log(f"  ! {type(e).__name__} on {path} — skipping")
            return None
        die(f"{type(e).__name__} calling {path}: {e}")


def fetch_repos():
    repos, page = [], 1
    while page <= 10:  # hard stop, never loop forever
        batch = api(f"/users/{USER}/repos?per_page=100&page={page}&sort=pushed")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    keep = [
        r for r in repos
        if not r.get("fork") and not r.get("archived")
        and not r.get("private") and r["name"] not in EXCLUDE
    ]
    log(f"Fetched {len(repos)} repos, {len(keep)} eligible after filtering.")
    return keep


def score(r):
    """Rank by impact, then by recency of the last push."""
    return (
        r.get("stargazers_count", 0) * 10
        + r.get("forks_count", 0) * 5
        + (2 if r.get("description") else 0),
        r.get("pushed_at", ""),
    )


def languages(repo_name, primary):
    """Top 3 languages actually used in the repo."""
    data = api(f"/repos/{USER}/{repo_name}/languages", optional=True)
    if data:
        return sorted(data, key=data.get, reverse=True)[:3]
    return [primary] if primary else []


def cell(text):
    """Make arbitrary text safe inside a markdown table cell."""
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )


def build_block(repos):
    ranked = sorted(repos, key=score, reverse=True)
    cards, rows = ranked[:CARD_COUNT], ranked[:TABLE_COUNT]

    # No pinned-card images: those came from github-readme-stats.vercel.app,
    # which is rate-limited and rendered as broken images. Plain markdown
    # instead — nothing external to fail.
    out = ["| Project | What it does | Stack | ⭐ | Live |",
           "| :--- | :--- | :--- | :---: | :---: |"]
    for r in rows:
        desc = cell(r.get("description")) or "_No description yet._"
        stack = " ".join(f"`{l}`" for l in languages(r["name"], r.get("language")))
        home = (r.get("homepage") or "").strip()
        live = f"[↗]({home})" if home.startswith("http") else "—"
        out.append(
            f'| **[{cell(r["name"])}]({r["html_url"]})** | {desc} | {stack} '
            f'| {r.get("stargazers_count", 0)} | {live} |'
        )

    highlight = cards[0] if cards else None
    if highlight:
        out += ["", f'<sub>Most active right now: '
                    f'<a href="{highlight["html_url"]}">{cell(highlight["name"])}</a></sub>']

    return "\n".join(out)


def main():
    if not os.path.exists(README):
        die(f"{README} not found. cwd={os.getcwd()} contents={sorted(os.listdir('.'))[:25]}")

    with open(README, encoding="utf-8") as f:
        content = f.read()

    s, e = content.find(START), content.find(END)
    if s == -1 or e == -1 or e < s:
        die(f"Markers not found in {README}. It needs both {START} and {END}, in that order.")

    repos = fetch_repos()
    if not repos:
        log("No eligible repos — leaving the README untouched.")
        return

    # Slice, don't re.sub: descriptions can contain backslashes that
    # re.sub would try to interpret as escape sequences and crash on.
    new = content[:s] + f"{START}\n{build_block(repos)}\n" + content[e:]

    if new == content:
        log("No changes.")
        return

    with open(README, "w", encoding="utf-8") as f:
        f.write(new)
    log(f"Updated {README} — {min(len(repos), CARD_COUNT)} cards, "
        f"{min(len(repos), TABLE_COUNT)} table rows.")


if __name__ == "__main__":
    main()
