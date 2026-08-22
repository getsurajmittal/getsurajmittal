#!/usr/bin/env python3
"""
Rebuilds the "Live Activity Feed" block in README.md from your public GitHub events.

Replaces the old jamesgeorge007/github-activity-readme action, which is unmaintained
and still ships a Node runtime GitHub has deprecated.

Run locally:   GITHUB_TOKEN=ghp_xxx python3 scripts/update_activity.py
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("GH_USERNAME", "getsurajmittal")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = os.environ.get("README_PATH", "README.md")
MAX_LINES = int(os.environ.get("MAX_LINES", "10"))

START, END = "<!--START_SECTION:activity-->", "<!--END_SECTION:activity-->"


def log(msg):
    print(msg, flush=True)


def die(msg):
    print(f"::error::{msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def ago(iso):
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return ""
    secs = (datetime.now(timezone.utc) - then).total_seconds()
    for limit, div, unit in ((3600, 60, "m"), (86400, 3600, "h"), (2592000, 86400, "d")):
        if secs < limit:
            return f" · {int(secs // div)}{unit} ago"
    return f" · {int(secs // 2592000)}mo ago"


def repo_link(ev):
    name = ev.get("repo", {}).get("name", "")
    return f"[{name}](https://github.com/{name})" if name else "a repo"


def describe(ev):
    t, p = ev.get("type"), ev.get("payload", {})
    r = repo_link(ev)

    if t == "PushEvent":
        n = p.get("size", 0) or len(p.get("commits", []))
        return f"⬆️ Pushed {n} commit{'s' if n != 1 else ''} to {r}"
    if t == "CreateEvent":
        kind = p.get("ref_type", "ref")
        return f"✨ Created a new {kind} in {r}" if kind != "repository" else f"🎉 Created new repository {r}"
    if t == "PullRequestEvent":
        act = p.get("action", "opened")
        if act == "closed" and p.get("pull_request", {}).get("merged"):
            act = "merged"
        num = p.get("number", "")
        return f"🔀 {act.capitalize()} PR #{num} in {r}"
    if t == "IssuesEvent":
        return f"📌 {p.get('action', 'opened').capitalize()} issue #{p.get('issue', {}).get('number', '')} in {r}"
    if t == "IssueCommentEvent":
        return f"💬 Commented on #{p.get('issue', {}).get('number', '')} in {r}"
    if t == "WatchEvent":
        return f"⭐ Starred {r}"
    if t == "ForkEvent":
        return f"🍴 Forked {r}"
    if t == "ReleaseEvent":
        return f"🚀 Released {p.get('release', {}).get('tag_name', '')} in {r}"
    if t == "PullRequestReviewEvent":
        return f"👀 Reviewed a PR in {r}"
    if t == "DeleteEvent":
        return f"🗑️ Deleted a {p.get('ref_type', 'ref')} in {r}"
    return None  # unknown / noisy event type — skip it


def fetch_events():
    req = urllib.request.Request(
        f"https://api.github.com/users/{USER}/events/public?per_page=100",
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
        die(f"GitHub API {e.code} fetching events"
            + (" (rate limited — is GITHUB_TOKEN set?)" if e.code == 403 else ""))
    except Exception as e:
        die(f"{type(e).__name__} fetching events: {e}")


def main():
    if not os.path.exists(README):
        die(f"{README} not found. cwd={os.getcwd()}")

    with open(README, encoding="utf-8") as f:
        content = f.read()

    s, e = content.find(START), content.find(END)
    if s == -1 or e == -1 or e < s:
        die(f"Markers not found in {README}. It needs both {START} and {END}, in that order.")

    lines = []
    for ev in fetch_events():
        text = describe(ev)
        if text:
            lines.append(f"{len(lines) + 1}. {text}{ago(ev.get('created_at', ''))}")
        if len(lines) >= MAX_LINES:
            break

    if not lines:
        lines = ["_No public activity in the last 90 days — heads down on something._"]

    body = "\n".join(lines)
    new = content[:s] + f"{START}\n\n{body}\n\n" + content[e:]

    if new == content:
        log("No changes.")
        return

    with open(README, "w", encoding="utf-8") as f:
        f.write(new)
    log(f"Updated {README} — {len(lines)} activity lines.")


if __name__ == "__main__":
    main()
