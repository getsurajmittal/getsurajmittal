#!/usr/bin/env python3
"""
Rebuilds the "Featured Projects" block in README.md straight from the GitHub API.

Any repo you create, rename, describe or push to shows up automatically the next
time this runs — no manual editing of the README ever again.

Run locally:   GITHUB_TOKEN=ghp_xxx python scripts/update_projects.py
In Actions:    handled by .github/workflows/readme-autoupdate.yml
"""

import json
import os
import re
import sys
import urllib.request

USER = os.environ.get("GH_USERNAME", "getsurajmittal")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = os.environ.get("README_PATH", "README.md")

# How many repos to show as pinned-style cards (must be an even number for a tidy grid)
CARD_COUNT = int(os.environ.get("CARD_COUNT", "4"))
# How many rows in the details table
TABLE_COUNT = int(os.environ.get("TABLE_COUNT", "6"))

# Repos you never want listed (the profile repo itself, forks, experiments...)
EXCLUDE = {n.strip() for n in os.environ.get("EXCLUDE_REPOS", USER).split(",") if n.strip()}

THEME = (
    "hide_border=true&theme=tokyonight&bg_color=0D1117"
    "&title_color=00F5D4&icon_color=8B5CF6&text_color=C9D1D9"
)

START, END = "<!-- PROJECTS:START -->", "<!-- PROJECTS:END -->"


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "profile-readme-updater",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_repos():
    repos, page = [], 1
    while True:
        batch = api(f"/users/{USER}/repos?per_page=100&page={page}&sort=pushed")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return [
        r for r in repos
        if not r.get("fork") and not r.get("archived")
        and not r.get("private") and r["name"] not in EXCLUDE
    ]


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
    try:
        data = api(f"/repos/{USER}/{repo_name}/languages")
        return sorted(data, key=data.get, reverse=True)[:3] or ([primary] if primary else [])
    except Exception:
        return [primary] if primary else []


def build_block(repos):
    ranked = sorted(repos, key=score, reverse=True)
    cards = ranked[:CARD_COUNT]
    rows = ranked[:TABLE_COUNT]

    out = ["<div align=\"center\">", ""]
    for i in range(0, len(cards), 2):
        pair = cards[i:i + 2]
        line = " ".join(
            f'<a href="{r["html_url"]}"><img width="49%" '
            f'src="https://github-readme-stats.vercel.app/api/pin/?username={USER}'
            f'&repo={r["name"]}&{THEME}" alt="{r["name"]}" /></a>'
            for r in pair
        )
        out += [line, ""]
    out += ["</div>", ""]

    out += ["| Project | What it does | Stack | ⭐ |", "| :--- | :--- | :--- | :---: |"]
    for r in rows:
        desc = (r.get("description") or "_No description yet._").replace("|", "\\|")
        stack = " ".join(f"`{l}`" for l in languages(r["name"], r.get("language")))
        out.append(
            f'| **[{r["name"]}]({r["html_url"]})** | {desc} | {stack} | {r.get("stargazers_count", 0)} |'
        )

    return "\n".join(out)


def main():
    with open(README, encoding="utf-8") as f:
        content = f.read()

    if START not in content or END not in content:
        sys.exit(f"Markers {START} / {END} not found in {README}")

    block = build_block(fetch_repos())
    updated = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        f"{START}\n{block}\n{END}",
        content,
        flags=re.DOTALL,
    )

    if updated == content:
        print("No changes.")
        return

    with open(README, "w", encoding="utf-8") as f:
        f.write(updated)
    print("README.md projects section updated.")


if __name__ == "__main__":
    main()