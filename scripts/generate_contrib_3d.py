import json
import os
import urllib.request

USERNAME = os.environ.get("GH_USERNAME", "SSManikandaprabu")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
OUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "contrib-3d.svg",
)


def fetch_contributions(username: str) -> dict:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN environment variable is required")
    query = (
        "query($login: String!) { user(login: $login) { "
        "contributionsCollection { contributionCalendar { totalContributions "
        "weeks { contributionDays { date contributionCount } } } } } }"
    )
    payload = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "contrib-3d-generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def build_contrib_3d_svg(cal: dict) -> str:
    w, h = 920, 440
    weeks = cal["weeks"][-52:]
    total = cal["totalContributions"]
    num_cols = len(weeks)
    num_rows = 7

    max_day_count = 0
    active_days = 0
    for wk in weeks:
        for day in wk["contributionDays"]:
            c = day["contributionCount"]
            if c > 0:
                active_days += 1
            if c > max_day_count:
                max_day_count = c

    dxh, dyh, gap = 10.6, 4.9, 0.86
    origin_x, origin_y = 232.0, 104.0

    def iso_pt(col: float, row: float, z: float = 0.0):
        return (origin_x + (col - row) * dxh, origin_y + (col + row) * dyh - z)

    def pts(arr):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in arr)

    pad = 0.85
    p_n = iso_pt(-pad, -pad, -4)
    p_e = iso_pt(num_cols - 1 + pad, -pad, -4)
    p_s = iso_pt(num_cols - 1 + pad, num_rows - 1 + pad, -4)
    p_w = iso_pt(-pad, num_rows - 1 + pad, -4)
    slab_depth = 20.0
    pb_e = (p_e[0], p_e[1] + slab_depth)
    pb_s = (p_s[0], p_s[1] + slab_depth)
    pb_w = (p_w[0], p_w[1] + slab_depth)
    ps_n = (p_n[0], p_n[1] + slab_depth + 12)
    ps_e = (p_e[0] + 10, p_e[1] + slab_depth + 14)
    ps_s = (p_s[0], p_s[1] + slab_depth + 18)
    ps_w = (p_w[0] - 10, p_w[1] + slab_depth + 14)

    platform_svg = (
        f'<polygon points="{pts([ps_n, ps_e, ps_s, ps_w])}" fill="#04030a" fill-opacity="0.9" />\n'
        f'<polygon points="{pts([p_w, p_s, pb_s, pb_w])}" fill="#231c42" stroke="#413575" stroke-width="1" />\n'
        f'<polygon points="{pts([p_s, p_e, pb_e, pb_s])}" fill="#151029" stroke="#31275c" stroke-width="1" />\n'
        f'<polygon points="{pts([p_n, p_e, p_s, p_w])}" fill="#17132e" stroke="#4e408a" stroke-width="1.2" />\n'
        f'<polyline points="{pts([p_w, p_s, p_e])}" fill="none" stroke="#A9FEF7" stroke-opacity="0.7" stroke-width="1.6" />\n'
        f'<polyline points="{pts([pb_w, pb_s, pb_e])}" fill="none" stroke="#FE428E" stroke-opacity="0.6" stroke-width="1.2" />\n'
    )

    months_svg = []
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    last_month = None
    for c_idx, wk in enumerate(weeks):
        if not wk["contributionDays"]:
            continue
        m_num = int(wk["contributionDays"][0]["date"].split("-")[1])
        if m_num != last_month and c_idx % 4 != 3:
            last_month = m_num
            mx, my = iso_pt(c_idx, num_rows + 1.5, -24)
            months_svg.append(
                f'<text x="{mx:.1f}" y="{my:.1f}" fill="#A9FEF7" fill-opacity="0.78" '
                f'font-family="Consolas, \'Courier New\', monospace" font-size="10.5" font-weight="600">{month_names[m_num - 1]}</text>'
            )

    cells = []
    for c_idx, wk in enumerate(weeks):
        for r_idx, day in enumerate(wk["contributionDays"]):
            cells.append((c_idx + r_idx, c_idx, r_idx, day["contributionCount"]))
    cells.sort(key=lambda item: (item[0], item[1]))

    def style_for(count: int):
        if count <= 0:
            return ("#211d3a", "#17142b", "#100e20", "#322c57", False)
        if count <= 2:
            return ("#f472b6", "#be2e78", "#7d194d", "#fbcfe8", False)
        if count <= 4:
            return ("#ff6fb0", "#e62e7a", "#9e174e", "#ffc2de", True)
        if count <= 7:
            return ("#fde047", "#eab308", "#a16207", "#fef9c3", True)
        return ("#a9fef7", "#06b6d4", "#0e7490", "#e0fffe", True)

    bars = []
    for _, c_idx, r_idx, count in cells:
        cx, cy = iso_pt(c_idx, r_idx, 0)
        top_c, left_c, right_c, edge_c, tall = style_for(count)
        bar_h = 5.0 if count == 0 else min(92.0, 16.0 + count * 11.0)
        rx, ry = dxh * gap, dyh * gap

        t_n, t_e, t_s, t_w = (cx, cy - ry - bar_h), (cx + rx, cy - bar_h), (cx, cy + ry - bar_h), (cx - rx, cy - bar_h)
        b_e, b_s, b_w = (cx + rx, cy), (cx, cy + ry), (cx - rx, cy)

        if count == 0:
            bars.append(
                f'<polygon points="{pts([t_w, t_s, b_s, b_w])}" fill="{left_c}" />\n'
                f'<polygon points="{pts([t_s, t_e, b_e, b_s])}" fill="{right_c}" />\n'
                f'<polygon points="{pts([t_n, t_e, t_s, t_w])}" fill="{top_c}" stroke="{edge_c}" stroke-width="0.65" />'
            )
        else:
            delay = round((c_idx / max(1, num_cols)) * 1.1, 2)
            bands = []
            if bar_h >= 28:
                for s in range(1, int((bar_h - 10) // 10) + 1):
                    z_off = s * 9.5
                    wl_a, wl_b = (cx - rx * 0.72, cy - ry * 0.28 - z_off), (cx - rx * 0.15, cy + ry * 0.65 - z_off)
                    wr_a, wr_b = (cx + rx * 0.15, cy + ry * 0.65 - z_off), (cx + rx * 0.72, cy - ry * 0.28 - z_off)
                    bands.append(
                        f'<line x1="{wl_a[0]:.1f}" y1="{wl_a[1]:.1f}" x2="{wl_b[0]:.1f}" y2="{wl_b[1]:.1f}" stroke="#ffffff" stroke-opacity="0.45" stroke-width="1.2" />\n'
                        f'<line x1="{wr_a[0]:.1f}" y1="{wr_a[1]:.1f}" x2="{wr_b[0]:.1f}" y2="{wr_b[1]:.1f}" stroke="#ffffff" stroke-opacity="0.25" stroke-width="1.2" />'
                    )
            beacon = ""
            if tall:
                spire_y = cy - bar_h - 9.5
                beacon = (
                    f'<line x1="{cx:.1f}" y1="{cy - bar_h:.1f}" x2="{cx:.1f}" y2="{spire_y:.1f}" stroke="{edge_c}" stroke-width="1.2" stroke-opacity="0.85" />\n'
                    f'<circle cx="{cx:.1f}" cy="{spire_y:.1f}" r="2.4" fill="{top_c}">'
                    f'<animate attributeName="opacity" values="0.35;1;0.35" dur="2.0s" begin="{delay}s" repeatCount="indefinite" /></circle>'
                )
            bars.append(
                f'<g><polygon points="{pts([t_w, t_s, b_s, b_w])}" fill="{left_c}" />'
                f'<polygon points="{pts([t_s, t_e, b_e, b_s])}" fill="{right_c}" />'
                f'<polygon points="{pts([t_n, t_e, t_s, t_w])}" fill="{top_c}" stroke="{edge_c}" stroke-width="0.75" />'
                f'<line x1="{t_s[0]:.1f}" y1="{t_s[1]:.1f}" x2="{b_s[0]:.1f}" y2="{b_s[1]:.1f}" stroke="{edge_c}" stroke-opacity="0.85" stroke-width="1.0" />'
                f'{"".join(bands)}{beacon}</g>'
            )

    def hud_card(x: int, y: int, label: str, value: str, accent: str):
        return (
            f'<g><rect x="{x}" y="{y}" width="176" height="52" rx="10" fill="#141129" stroke="{accent}" stroke-opacity="0.6" stroke-width="1.2" />'
            f'<rect x="{x+10}" y="{y+12}" width="3.5" height="28" rx="1.75" fill="{accent}" />'
            f'<text x="{x+22}" y="{y+22}" fill="#a6a0cc" font-family="Consolas, \'Courier New\', monospace" font-size="10" letter-spacing="1">{label}</text>'
            f'<text x="{x+22}" y="{y+41}" fill="#FFFFFF" font-family="\'Segoe UI\', Ubuntu, sans-serif" font-size="16" font-weight="700">{value}</text></g>'
        )

    hud_cards = (
        hud_card(28, 240, "YEARLY COMMITS", f"{total} Total", "#FE428E")
        + hud_card(28, 302, "PEAK DAILY OUTPUT", f"{max_day_count} Contributions", "#F8D847")
        + hud_card(28, 364, "ACTIVE CODING DAYS", f"{active_days} Days", "#A9FEF7")
    )

    bg_grid = []
    for k in range(-12, 22):
        x1, x2 = -120 + k * 70, -120 + k * 70 + 480
        bg_grid.append(f'<line x1="{x1}" y1="{h}" x2="{x2}" y2="70" stroke="#2a224d" stroke-opacity="0.35" stroke-width="1" />')
        bg_grid.append(f'<line x1="{x1}" y1="70" x2="{x2}" y2="{h}" stroke="#2a224d" stroke-opacity="0.25" stroke-width="1" />')

    def mini_iso_crystal(cx_cr: int, cy_cr: int, s: int, top_col: str, left_col: str, right_col: str, dur: str):
        return (
            f'<g><animateTransform attributeName="transform" type="translate" values="0,-6;0,6;0,-6" dur="{dur}" repeatCount="indefinite" />'
            f'<polygon points="{cx_cr},{cy_cr-s} {cx_cr+s*0.86},{cy_cr-s*0.5} {cx_cr},{cy_cr} {cx_cr-s*0.86},{cy_cr-s*0.5}" fill="{top_col}" stroke="#e0fffe" stroke-width="1" />'
            f'<polygon points="{cx_cr-s*0.86},{cy_cr-s*0.5} {cx_cr},{cy_cr} {cx_cr},{cy_cr+s} {cx_cr-s*0.86},{cy_cr+s*0.5}" fill="{left_col}" stroke="#FE428E" stroke-width="1" />'
            f'<polygon points="{cx_cr},{cy_cr} {cx_cr+s*0.86},{cy_cr-s*0.5} {cx_cr+s*0.86},{cy_cr+s*0.5} {cx_cr},{cy_cr+s}" fill="{right_col}" stroke="#A9FEF7" stroke-width="1" /></g>'
        )

    crystal = (
        mini_iso_crystal(842, 128, 24, "#A9FEF7", "#be2e78", "#0e7490", "4.2s")
        + mini_iso_crystal(776, 98, 13, "#F8D847", "#ca8a04", "#854d0e", "3.4s")
        + mini_iso_crystal(696, 132, 10, "#FE428E", "#9d174d", "#500724", "4.8s")
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" height="{h}">
  <defs>
    <linearGradient id="cbg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#090814" /><stop offset="55%" stop-color="#121022" /><stop offset="100%" stop-color="#1b1430" /></linearGradient>
    <radialGradient id="cityGlow" cx="68%" cy="62%" r="45%"><stop offset="0%" stop-color="#FE428E" stop-opacity="0.24" /><stop offset="55%" stop-color="#A9FEF7" stop-opacity="0.08" /><stop offset="100%" stop-color="#121022" stop-opacity="0" /></radialGradient>
    <clipPath id="cClip"><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="14" /></clipPath>
  </defs>
  <g clip-path="url(#cClip)">
    <rect x="0" y="0" width="{w}" height="{h}" fill="url(#cbg)" />{"".join(bg_grid)}<rect x="0" y="0" width="{w}" height="{h}" fill="url(#cityGlow)" />
    <text x="28" y="38" fill="#FE428E" font-family="'Segoe UI', Ubuntu, sans-serif" font-size="18" font-weight="800" letter-spacing="1.0">3D ISOMETRIC CONTRIBUTION METROPOLIS</text>
    <text x="28" y="58" fill="#A9FEF7" font-family="Consolas, 'Courier New', monospace" font-size="12">@{USERNAME}  ·  52-Week 3D Architecture  ·  Live GitHub Calendar</text>
    <text x="698" y="40" fill="#9a95b8" font-family="Consolas, 'Courier New', monospace" font-size="11">Less</text>
    <rect x="732" y="30" width="13" height="13" rx="3" fill="#1b1830" stroke="#3b3363" /><rect x="750" y="30" width="13" height="13" rx="3" fill="#d9468f" /><rect x="768" y="30" width="13" height="13" rx="3" fill="#FE428E" /><rect x="786" y="30" width="13" height="13" rx="3" fill="#F8D847" /><rect x="804" y="30" width="13" height="13" rx="3" fill="#A9FEF7" />
    <text x="824" y="40" fill="#9a95b8" font-family="Consolas, 'Courier New', monospace" font-size="11">More</text>
    {crystal}{platform_svg}{"".join(bars)}{"".join(months_svg)}{hud_cards}
  </g>
  <rect x="1" y="1" width="{w-2}" height="{h-2}" rx="14" fill="none" stroke="#453a75" stroke-width="1.5" />
</svg>'''


if __name__ == "__main__":
    cal = fetch_contributions(USERNAME)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(build_contrib_3d_svg(cal))
    print(f"Generated {OUT_PATH} ({cal['totalContributions']} contributions)")
