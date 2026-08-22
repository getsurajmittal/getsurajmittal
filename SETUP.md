# Setup — 5 minutes, then it runs itself

## 1. Drop the files in

Everything goes into your **profile repo**: `github.com/getsurajmittal/getsurajmittal`

```
getsurajmittal/
├── README.md
├── scripts/
│   ├── update_projects.py
│   └── update_activity.py
└── .github/
    └── workflows/
        ├── readme-autoupdate.yml
        └── snake.yml
```

```bash
git clone https://github.com/getsurajmittal/getsurajmittal.git
cd getsurajmittal
# copy the files in, then:
git add -A && git commit -m "feat: dynamic profile README 🚀" && git push
```

> ⚠️ `git add -A` matters. `git add .` from the wrong directory, or a stray `.gitignore`
> rule, is how `scripts/` ends up missing from the repo — which is exactly what produces
> **exit code 2**. Confirm with `git ls-files scripts/` before pushing; it must list both
> `.py` files.

## 2. Turn on write access for Actions

**Settings → Actions → General → Workflow permissions** → select
**"Read and write permissions"** → Save.

Without this the bot can't commit the updated README back.

## 3. Kick off the first run

**Actions** tab → `🐍 Generate contribution snake` → **Run workflow**, then the same for
`🔄 Auto-update README`. The snake needs one run to create the `output` branch; until then
that image shows as broken. Expected.

---

## Where to make future changes

### The one rule

`README.md` is **yours to edit freely — except inside these two blocks**, which the bot
rewrites from scratch on every run:

```
<!-- PROJECTS:START -->        ...anything here is overwritten...   <!-- PROJECTS:END -->
<!--START_SECTION:activity-->  ...anything here is overwritten...   <!--END_SECTION:activity-->
```

Edit inside those and your change disappears within six hours, silently. To change what
appears there, edit the *script* that generates it, not the README.

### What to touch for what

| You want to change | File | Where in it |
| :--- | :--- | :--- |
| Bio, headline, tech badges, trophies, stats cards, footer quote, section order | `README.md` | Directly — it's plain markdown |
| Typing-animation lines | `README.md` | The `readme-typing-svg` URL, `lines=` param (`;` separates lines, URL-encode spaces as `+`) |
| How many project cards / table rows | `readme-autoupdate.yml` | `CARD_COUNT`, `TABLE_COUNT` under `env:` |
| Hide a repo from the projects list | `readme-autoupdate.yml` | `EXCLUDE_REPOS` — comma-separated |
| How many activity lines | `readme-autoupdate.yml` | `MAX_LINES` under `env:` |
| Table columns, ranking order, card layout | `scripts/update_projects.py` | `build_block()` and `score()` |
| Activity wording or emoji | `scripts/update_activity.py` | `describe()` |
| How often it all runs | both workflows | the `cron:` lines |
| Snake colours | `snake.yml` | `color_snake` / `color_dots` in `outputs:` |

### Two gotchas

**Theme colours live in two places.** The static widgets are themed inline in `README.md`;
the generated project cards are themed by the `THEME` constant in `update_projects.py`.
Change one without the other and the projects section stops matching the rest of the page.

**So does your username.** Hardcoded throughout `README.md`, and set as `GH_USERNAME` in
`readme-autoupdate.yml`. Only relevant if you ever rename your account.

### Workflow

Small text tweak → edit `README.md` in GitHub's web editor, commit. Done.

Anything touching the scripts → clone, edit, test locally first, then push:

```bash
GITHUB_TOKEN=ghp_xxx python3 scripts/update_projects.py && git diff README.md
```

That shows you exactly what the bot would commit, before it commits it. Editing `README.md`
won't retrigger the workflow (`paths-ignore`), so run it manually from the **Actions** tab
if you want to see the result immediately.

---

## Troubleshooting

### "Process completed with exit code 2"

That is Python's *"can't open file"* code — the interpreter never ran your script, so the
script itself isn't the problem. In practice it means `scripts/update_projects.py` isn't in
the repository at that path on the branch being checked out. Usual causes:

- `scripts/` was never committed (see the `git add -A` note above)
- the files were committed to a different branch than the one Actions checks out
- the folder is named `script/` or `Scripts/` — the runner is case-sensitive, your laptop may not be

The workflow now has a **Preflight** step that lists the repo contents and prints
`OK` / `MISSING` per file, so the log tells you which one it is instead of a bare exit code.

### Other failures

| Symptom in the log | Cause | Fix |
| :--- | :--- | :--- |
| `Permission to ... denied` on push | Workflow permissions still read-only | Step 2 above |
| `GitHub API 403 (rate limited)` | `GITHUB_TOKEN` not passed to the step | Keep the `env:` block on the script steps |
| `Markers not found` | The `<!-- PROJECTS:START -->` / `:END` comments were edited or deleted | Restore both, in that order |
| Push rejected, non-fast-forward | Two runs raced | Already handled by the `concurrency:` group and `git pull --rebase` |

---

## What changed in this version

**Node 20 deprecation.** `actions/checkout` → **v6**, `actions/setup-python` → **v6**,
`crazy-max/ghaction-github-pages` → **v5**. All three run on Node 24 now.

`Platane/snk@v3` still ships a Node 20 runtime, so the snake job keeps logging that warning.
It's a warning, not an error — the action works. Nothing to do until upstream updates.

**Dropped `jamesgeorge007/github-activity-readme`.** It's unmaintained and pinned to an even
older runtime, so it was the next thing due to break. `scripts/update_activity.py` replaces
it with ~40 lines against the events API — no third-party dependency, same output, and it
understands merged PRs and releases, which the action didn't.

**Fixed a latent crash.** The old script rebuilt the README with `re.sub`, which interprets
backslashes in the *replacement* text. Any repo description containing one — `C:\path`,
a regex, a Windows path — would have killed the job with `re.error: bad escape`. It now
splices by string index, so descriptions are treated as literal text.

**Merged the two jobs into one.** They previously checked out and pushed separately, which
could race and cause non-fast-forward push failures. One job, one commit, plus a
`concurrency:` group so a scheduled run and a push run can't overlap.

**`paths-ignore: README.md`** on the push trigger, so the bot's own commit doesn't retrigger
the workflow in a loop.

---

## What updates on its own, and when

| Thing | Refreshes | How |
| :--- | :--- | :--- |
| Stats card, streak, top languages, activity graph, trophies | Every page load | Live SVGs rendered on request |
| Profile views, follower count, repo count | Every page load | Live badges |
| **Featured Projects** (cards + table) | Every 6 h, every push, on demand | `update_projects.py` |
| **Live Activity Feed** | Every 6 h | `update_activity.py` |
| **Contribution snake** | Every 12 h | `Platane/snk` |

Create a repo, push code, get a star, change a description — within six hours the README
reflects it with zero effort from you.

### Want it instant instead of every 6 hours?

Add this to **any other repo** and its pushes poke your profile immediately:

```yaml
name: Ping profile README
on: [push, create]
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - run: |
          curl -X POST \
            -H "Accept: application/vnd.github+json" \
            -H "Authorization: Bearer ${{ secrets.PROFILE_PAT }}" \
            https://api.github.com/repos/getsurajmittal/getsurajmittal/dispatches \
            -d '{"event_type":"refresh-readme"}'
```

`PROFILE_PAT` = a fine-grained personal access token with **Contents: write** on your
profile repo, saved as a repository secret in the other repo.

---

## Tuning

Environment variables in `readme-autoupdate.yml`:

| Variable | Default | Does |
| :--- | :--- | :--- |
| `CARD_COUNT` | `4` | Pinned-style cards (keep it even) |
| `TABLE_COUNT` | `6` | Rows in the details table |
| `EXCLUDE_REPOS` | `getsurajmittal` | Comma-separated repos to hide |
| `MAX_LINES` | `10` | Activity feed entries |

Forks, archived and private repos are skipped automatically. Ranking is stars → forks →
has-a-description → most recently pushed, so **adding a description is the fastest way to
promote a repo**. Repos without one render as *"No description yet."*

### Run it locally before pushing

```bash
GITHUB_TOKEN=ghp_xxx python3 scripts/update_projects.py
GITHUB_TOKEN=ghp_xxx python3 scripts/update_activity.py
git diff README.md
```

Both scripts are idempotent — running twice in a row produces no second change.

---

## Also worth knowing

**Public widget services get rate-limited.** `github-readme-stats` and `streak-stats` are
free shared instances; under load a card occasionally renders an error image.
[Deploy your own to Vercel](https://github.com/anuraghazra/github-readme-stats#deploy-on-your-own)
(free, ~3 min) and swap the domain in the README if it bothers you.

**Optional Wakatime card.** Only fills in if you sign up at [wakatime.com](https://wakatime.com),
install the IDE plugin, and make your profile public. Otherwise delete the `api/wakatime`
image line and widen the top-languages card to `98%`.
