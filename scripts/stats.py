#!/usr/bin/env python3
"""
Renders assets/generated/stats.svg: a "die report" card with live GitHub stats,
a contribution heat-map drawn as an SRAM bit-cell array, and top languages.

Runs daily in .github/workflows/stats.yml with the built-in GITHUB_TOKEN,
so it never depends on third-party stats servers being up.

Local test without network:  python3 scripts/stats.py --demo
"""
import datetime as dt
import json
import os
import sys
import urllib.request

USER = os.environ.get("PROFILE_USER", "divyanshmishra1")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "generated", "stats.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
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
      totalPullRequestContributions
      totalIssueContributions
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
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": f"{USER}-profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def demo():
    import random
    random.seed(7)
    today = dt.date.today()
    start = today - dt.timedelta(days=364 + today.weekday() + 1)
    weeks = []
    for w in range(53):
        days = []
        for d in range(7):
            day = start + dt.timedelta(days=w * 7 + d)
            if day > today:
                break
            days.append({"date": day.isoformat(), "contributionCount": random.choice([0, 0, 1, 2, 3, 5, 8, 12])})
        weeks.append({"contributionDays": days})
    return {
        "followers": {"totalCount": 64},
        "pullRequests": {"totalCount": 31},
        "repositories": {"totalCount": 18, "nodes": [
            {"stargazerCount": 3, "languages": {"edges": [
                {"size": 90000, "node": {"name": "Verilog", "color": "#b2b7f8"}},
                {"size": 40000, "node": {"name": "SystemVerilog", "color": "#DAE1C2"}},
                {"size": 20000, "node": {"name": "Tcl", "color": "#e4cc98"}},
                {"size": 15000, "node": {"name": "Python", "color": "#3572A5"}},
                {"size": 9000, "node": {"name": "C", "color": "#555555"}}]}}]},
        "contributionsCollection": {
            "totalCommitContributions": 412, "totalPullRequestContributions": 27,
            "totalIssueContributions": 9, "restrictedContributionsCount": 120,
            "contributionCalendar": {"totalContributions": 980, "weeks": weeks}},
    }


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    longest = cur = 0
    for c in counts:
        cur = cur + 1 if c > 0 else 0
        longest = max(longest, cur)
    current = 0
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:  # today may not have activity yet
        i -= 1
    while i >= 0 and counts[i] > 0:
        current += 1
        i -= 1
    return current, longest


def fmt(n):
    return f"{n/1000:.1f}k" if n >= 10000 else f"{n:,}"


def render(u):
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    cur, longest = streaks(days)
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])

    langs = {}
    colors = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            langs[n] = langs.get(n, 0) + e["size"]
            colors[n] = e["node"]["color"] or "#8B949E"
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:6]

    W, H = 1200, 360
    MONO = 'ui-monospace,SFMono-Regular,Menlo,Consolas,&quot;Liberation Mono&quot;,monospace'
    SANS = '-apple-system,BlinkMacSystemFont,&quot;Segoe UI&quot;,Helvetica,Arial,sans-serif'
    out = []

    # ---- metric "registers" (left) ----
    metrics = [
        ("CONTRIB_YR", fmt(cal["totalContributions"]), "contributions · last year"),
        ("COMMITS_YR", fmt(cc["totalCommitContributions"]), "commits · last year"),
        ("STREAK_CUR", f"{cur}d", f"current streak · best {longest}d"),
        ("PR_TOTAL", fmt(u["pullRequests"]["totalCount"]), "pull requests"),
        ("REPOS", fmt(u["repositories"]["totalCount"]), "public repositories"),
        ("STARS", fmt(stars), "stars earned"),
    ]
    for i, (reg, val, label) in enumerate(metrics):
        col, row = i % 2, i // 2
        x, y = 40 + col * 205, 66 + row * 92
        tint = ["#F2B705", "#FDE68A", "#22D3EE"][i % 3]
        out.append(f'<rect x="{x}" y="{y}" width="190" height="80" rx="10" fill="#111722" stroke="#263042"/>')
        out.append(f'<text x="{x+14}" y="{y+20}" font-family="{MONO}" font-size="10.5" fill="#5B6676" letter-spacing="1.5">{reg}</text>')
        out.append(f'<text x="{x+14}" y="{y+50}" font-family="{SANS}" font-size="28" font-weight="800" fill="{tint}">{val}</text>')
        out.append(f'<text x="{x+14}" y="{y+68}" font-family="{SANS}" font-size="11.5" fill="#8B949E">{label}</text>')

    # ---- heat-map as SRAM bit-cell array (right) ----
    weeks = cal["weeks"][-38:]
    mx = max([d["contributionCount"] for w in weeks for d in w["contributionDays"]] + [1])
    levels = ["#161B22", "#3B2F0B", "#6B5410", "#A67C0B", "#F2B705"]
    hx, hy, cs = 470, 98, 15
    out.append(f'<text x="{hx}" y="80" font-family="{MONO}" font-size="11" fill="#5B6676" letter-spacing="2">SRAM_ACTIVITY[7][{len(weeks)}] · each cell = one day</text>')
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            wd = (dt.date.fromisoformat(d["date"]).weekday() + 1) % 7
            c = d["contributionCount"]
            lvl = 0 if c == 0 else min(4, 1 + int(3 * c / mx))
            out.append(f'<rect x="{hx + wi*(cs+3)}" y="{hy + wd*(cs+3)}" width="{cs}" height="{cs}" rx="3" fill="{levels[lvl]}"><title>{d["date"]}: {c}</title></rect>')
    ly = hy + 7 * (cs + 3) + 14
    out.append(f'<text x="{hx}" y="{ly+10}" font-family="{MONO}" font-size="10.5" fill="#5B6676">0</text>')
    for i, c in enumerate(levels):
        out.append(f'<rect x="{hx + 14 + i*16}" y="{ly}" width="12" height="12" rx="2" fill="{c}"/>')
    out.append(f'<text x="{hx + 14 + 5*16 + 4}" y="{ly+10}" font-family="{MONO}" font-size="10.5" fill="#5B6676">max</text>')

    # ---- language bar (bottom right) ----
    bx, by, bw = hx, ly + 50, W - hx - 40
    out.append(f'<text x="{bx}" y="{by-8}" font-family="{MONO}" font-size="11" fill="#5B6676" letter-spacing="2">TOP LANGUAGES · BY BYTES</text>')
    x = bx
    for name, size in top:
        w = bw * size / (sum(s for _, s in top) or 1)
        out.append(f'<rect x="{x:.1f}" y="{by}" width="{max(w-2,1):.1f}" height="10" rx="3" fill="{colors[name]}"/>')
        x += w
    x = bx
    for name, size in top:
        pct = 100 * size / total
        out.append(f'<circle cx="{x+5}" cy="{by+30}" r="5" fill="{colors[name]}"/>'
                   f'<text x="{x+15}" y="{by+34}" font-family="{SANS}" font-size="12" fill="#C9D1D9">{name} <tspan fill="#5B6676">{pct:.0f}%</tspan></text>')
        x += 16 + len(name) * 7 + 44

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub stats for {USER}: {cal["totalContributions"]} contributions in the last year, current streak {cur} days, longest {longest} days, {u["pullRequests"]["totalCount"]} pull requests, {u["repositories"]["totalCount"]} public repositories, {stars} stars">
<rect width="{W}" height="{H}" rx="18" fill="#0A0E14"/>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="17" fill="none" stroke="#1F2937" stroke-width="2"/>
<text x="40" y="40" font-family="{MONO}" font-size="13" fill="#5B6676" letter-spacing="3">DIE REPORT · github.com/{USER}</text>
<text x="{W-40}" y="40" text-anchor="end" font-family="{MONO}" font-size="11" fill="#3A4456">regenerated {stamp} · GitHub Actions</text>
{''.join(out)}
</svg>'''
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {os.path.normpath(OUT)}")


if __name__ == "__main__":
    render(demo() if "--demo" in sys.argv else fetch())
