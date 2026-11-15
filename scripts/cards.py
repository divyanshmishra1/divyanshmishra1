#!/usr/bin/env python3
"""
Generates the GitHub stats cards shown on the profile README:

  assets/cards/stats.svg      overall stats
  assets/cards/streak.svg     total contributions, current and longest streak
  assets/cards/languages.svg  top languages
  assets/cards/activity.svg   contributions over the last 30 days

Runs daily from .github/workflows/cards.yml using the repository's built-in
GITHUB_TOKEN, so the cards never depend on public stats servers being up.
Style matches the "radical"-dark, green-accent theme used on the profile.

Local preview without network:  python3 scripts/cards.py --demo
"""
import datetime as dt
import json
import math
import os
import sys
import urllib.request

USER = os.environ.get("PROFILE_USER", "divyanshmishra1")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "cards")
HIDE_LANGS = {"Linker Script", "Makefile", "HTML", "CSS", "SCSS", "Dockerfile", "Batchfile", "CMake", "Procfile"}

BG, BORDER = "#0D1117", "#21262D"
TITLE, ICON, TEXT, MUTED = "#2ECC71", "#2ECC71", "#C9D1D9", "#8B949E"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}",
                 "Content-Type": "application/json", "User-Agent": f"{USER}-profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def demo():
    import random
    random.seed(3)
    today = dt.date.today()
    start = today - dt.timedelta(days=370)
    days = [{"date": (start + dt.timedelta(days=i)).isoformat(),
             "contributionCount": random.choice([0, 0, 0, 1, 2, 3, 6])} for i in range(371)]
    weeks = [{"contributionDays": days[i:i + 7]} for i in range(0, len(days), 7)]
    return {
        "name": "Divyansh Mishra", "followers": {"totalCount": 40},
        "pullRequests": {"totalCount": 5}, "issues": {"totalCount": 3},
        "repositoriesContributedTo": {"totalCount": 4},
        "repositories": {"totalCount": 7, "nodes": [{"stargazerCount": 2, "languages": {"edges": [
            {"size": 50000, "node": {"name": "Verilog", "color": "#b2b7f8"}},
            {"size": 30000, "node": {"name": "SystemVerilog", "color": "#DAE1C2"}},
            {"size": 20000, "node": {"name": "C", "color": "#555555"}},
            {"size": 12000, "node": {"name": "Python", "color": "#3572A5"}},
            {"size": 9000, "node": {"name": "Tcl", "color": "#e4cc98"}},
            {"size": 6000, "node": {"name": "TypeScript", "color": "#3178c6"}}]}}]},
        "contributionsCollection": {"totalCommitContributions": 120, "restrictedContributionsCount": 0,
                                    "contributionCalendar": {"totalContributions": 260, "weeks": weeks}},
    }


# ---------- helpers ----------
def card(w, h, title, body, label):
    t = f'<text x="25" y="35" fill="{TITLE}" font-size="18" font-weight="600">{title}</text>' if title else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">'
            f'<style>text{{font-family:{FONT}}}</style>'
            f'<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="6" fill="{BG}" stroke="{BORDER}"/>{t}{body}</svg>')


def fmt(n):
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


# Small line icons (drawn here, 16x16 box)
ICONS = {
    "star": '<path d="M8 1.5l1.9 4 4.4.5-3.3 3 .9 4.3L8 11.1 4.1 13.3 5 9 1.7 6l4.4-.5z" fill="none" stroke="{c}" stroke-width="1.4" stroke-linejoin="round"/>',
    "commit": '<circle cx="8" cy="8" r="3" fill="none" stroke="{c}" stroke-width="1.5"/><path d="M1 8h4M11 8h4" stroke="{c}" stroke-width="1.5"/>',
    "pr": '<circle cx="4" cy="3.5" r="1.8" fill="none" stroke="{c}" stroke-width="1.4"/><circle cx="4" cy="12.5" r="1.8" fill="none" stroke="{c}" stroke-width="1.4"/><circle cx="12" cy="12.5" r="1.8" fill="none" stroke="{c}" stroke-width="1.4"/><path d="M4 5.3v5.4M12 10.7V6.5a2 2 0 0 0-2-2H8" fill="none" stroke="{c}" stroke-width="1.4"/>',
    "issue": '<circle cx="8" cy="8" r="6" fill="none" stroke="{c}" stroke-width="1.4"/><circle cx="8" cy="8" r="1.4" fill="{c}"/>',
    "repo": '<path d="M3 2.5h9a1 1 0 0 1 1 1v10H4.5A1.5 1.5 0 0 1 3 12z M3 12a1.5 1.5 0 0 1 1.5-1.5H13" fill="none" stroke="{c}" stroke-width="1.4" stroke-linejoin="round"/>',
    "people": '<circle cx="6" cy="5.5" r="2.5" fill="none" stroke="{c}" stroke-width="1.4"/><path d="M1.5 13.5a4.5 4.5 0 0 1 9 0M11 3.5a2.3 2.3 0 0 1 0 4.4M12.5 13.5a4 4 0 0 0-1.5-3.2" fill="none" stroke="{c}" stroke-width="1.4" stroke-linecap="round"/>',
}


def icon(name, x, y):
    return f'<g transform="translate({x},{y})">{ICONS[name].format(c=ICON)}</g>'


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = cur = 0
    for c in counts:
        cur = cur + 1 if c else 0
        longest = max(longest, cur)
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1
    current = 0
    while i >= 0 and counts[i] > 0:
        current += 1
        i -= 1
    return current, longest


# ---------- cards ----------
def stats_card(u, days):
    cc = u["contributionsCollection"]
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    rows = [("star", "Total Stars Earned", stars),
            ("commit", "Commits (last year)", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
            ("pr", "Total PRs", u["pullRequests"]["totalCount"]),
            ("issue", "Total Issues", u["issues"]["totalCount"]),
            ("repo", "Contributed to (last year)", u["repositoriesContributedTo"]["totalCount"]),
            ("people", "Followers", u["followers"]["totalCount"])]
    body = []
    for i, (ic, label, val) in enumerate(rows):
        y = 62 + i * 22
        body.append(icon(ic, 25, y - 12))
        body.append(f'<text x="50" y="{y}" fill="{TEXT}" font-size="14" font-weight="600">{label}:</text>')
        body.append(f'<text x="255" y="{y}" fill="{TEXT}" font-size="14" font-weight="700">{fmt(val)}</text>')
    total = cc["contributionCalendar"]["totalContributions"]
    # ring: share of active days in the last year
    active = sum(1 for d in days[-365:] if d["contributionCount"])
    frac = active / 365
    r, cx, cy = 42, 395, 100
    circ = 2 * math.pi * r
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TITLE}" stroke-opacity=".2" stroke-width="6"/>')
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TITLE}" stroke-width="6" stroke-linecap="round" '
                f'stroke-dasharray="{circ*frac:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})"/>')
    body.append(f'<text x="{cx}" y="{cy+2}" text-anchor="middle" fill="{TEXT}" font-size="22" font-weight="700">{fmt(total)}</text>')
    body.append(f'<text x="{cx}" y="{cy+20}" text-anchor="middle" fill="{MUTED}" font-size="11">contributions</text>')
    body.append(f'<text x="{cx}" y="{cy+62}" text-anchor="middle" fill="{MUTED}" font-size="11">active {active} of 365 days</text>')
    name = (u.get("name") or USER).split()[0]
    return card(495, 195, f"{name}'s GitHub Stats", "".join(body),
                f"{name}'s GitHub stats: {stars} stars, {total} contributions in the last year")


def streak_card(days, total):
    cur, longest = streaks(days)
    first = days[0]["date"]

    def nice(s):
        return dt.date.fromisoformat(s).strftime("%b %-d, %Y")

    cols = [(82, fmt(total), "Total Contributions", f"{nice(first)} – Present"),
            (247, str(cur), "Current Streak", "days in a row"),
            (412, str(longest), "Longest Streak", "in the last year")]
    body = [f'<line x1="165" y1="28" x2="165" y2="170" stroke="{BORDER}"/>',
            f'<line x1="330" y1="28" x2="330" y2="170" stroke="{BORDER}"/>']
    for x, val, label, sub in cols:
        if label == "Current Streak":
            body.append(f'<circle cx="{x}" cy="71" r="40" fill="none" stroke="{TITLE}" stroke-width="5"/>')
            body.append(f'<text x="{x}" y="80" text-anchor="middle" fill="{TEXT}" font-size="28" font-weight="700">{val}</text>')
            body.append(f'<text x="{x}" y="140" text-anchor="middle" fill="{TITLE}" font-size="14" font-weight="700">{label}</text>')
            body.append(f'<text x="{x}" y="162" text-anchor="middle" fill="{MUTED}" font-size="12">{sub}</text>')
        else:
            body.append(f'<text x="{x}" y="80" text-anchor="middle" fill="{TEXT}" font-size="28" font-weight="700">{val}</text>')
            body.append(f'<text x="{x}" y="112" text-anchor="middle" fill="{TEXT}" font-size="14">{label}</text>')
            body.append(f'<text x="{x}" y="138" text-anchor="middle" fill="{MUTED}" font-size="12">{sub}</text>')
    return card(495, 195, "", "".join(body),
                f"{total} contributions in the last year, current streak {cur} days, longest streak {longest} days")


def languages_card(u):
    langs, colors = {}, {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            if n in HIDE_LANGS:
                continue
            langs[n] = langs.get(n, 0) + e["size"]
            colors[n] = e["node"]["color"] or MUTED
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:8]
    total = sum(s for _, s in top) or 1
    body = ['<clipPath id="bar"><rect x="25" y="55" width="445" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">']
    x = 25.0
    for n, s in top:
        w = 445 * s / total
        body.append(f'<rect x="{x:.1f}" y="55" width="{w:.1f}" height="8" fill="{colors[n]}"/>')
        x += w
    body.append("</g>")
    for i, (n, s) in enumerate(top):
        col, row = i % 2, i // 2
        lx, ly = 25 + col * 230, 92 + row * 25
        body.append(f'<circle cx="{lx+5}" cy="{ly-4}" r="5" fill="{colors[n]}"/>')
        body.append(f'<text x="{lx+16}" y="{ly}" fill="{TEXT}" font-size="12.5">{n} <tspan fill="{MUTED}">{100*s/total:.1f}%</tspan></text>')
    if not top:
        body.append(f'<text x="25" y="100" fill="{MUTED}" font-size="13">No public language data yet</text>')
    return card(495, 195, "Most Used Languages", "".join(body), "Most used languages: " +
                ", ".join(f"{n} {100*s/total:.0f}%" for n, s in top))


def activity_card(days):
    last = days[-30:]
    vals = [d["contributionCount"] for d in last]
    mx = max(vals + [4])
    x0, x1, y0, y1 = 45, 470, 160, 64
    step = (x1 - x0) / (len(vals) - 1)
    pts = [(x0 + i * step, y0 - (y0 - y1) * v / mx) for i, v in enumerate(vals)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"M{x0},{y0} L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f" L{x1},{y0} Z"
    body = []
    for k in range(5):
        gy = y0 - (y0 - y1) * k / 4
        body.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" stroke="{BORDER}"/>')
        body.append(f'<text x="{x0-8}" y="{gy+4:.1f}" text-anchor="end" fill="{MUTED}" font-size="10">{round(mx*k/4)}</text>')
    body.append(f'<path d="{area}" fill="{TITLE}" fill-opacity=".12"/>')
    body.append(f'<polyline points="{line}" fill="none" stroke="{TITLE}" stroke-width="2" stroke-linejoin="round"/>')
    for (x, y), d in zip(pts, last):
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{BG}" stroke="{TITLE}" stroke-width="1.5"><title>{d["date"]}: {d["contributionCount"]}</title></circle>')
    for i in (0, 10, 20, 29):
        lbl = dt.date.fromisoformat(last[i]["date"]).strftime("%d %b")
        body.append(f'<text x="{pts[i][0]:.1f}" y="180" text-anchor="middle" fill="{MUTED}" font-size="10">{lbl}</text>')
    return card(495, 195, "Contributions · last 30 days", "".join(body),
                f"Contributions over the last 30 days, peak {max(vals)} in a day")


def main():
    u = demo() if "--demo" in sys.argv else fetch()
    days = [d for w in u["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    os.makedirs(OUT, exist_ok=True)
    for name, svg in [("stats", stats_card(u, days)), ("streak", streak_card(days, u["contributionsCollection"]["contributionCalendar"]["totalContributions"])),
                      ("languages", languages_card(u)), ("activity", activity_card(days))]:
        with open(os.path.join(OUT, f"{name}.svg"), "w") as f:
            f.write(svg)
        print("wrote", name)


if __name__ == "__main__":
    main()
