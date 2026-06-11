"""Minutes-of-Meeting (MoM) export.

Collects the collaboration *activity* (status decisions + comments) in a date
range and renders it as a stakeholder-ready document (HTML / Markdown / CSV),
grouped by attribute (IS Reference Number). Intended to be circulated as the MoM
after a discussion on the V2.1->V1 conversion attributes.

Dates are matched against each event's local calendar day (timestamps are stored
in UTC; "changes done on that day" means the user's local day).
"""
from __future__ import annotations

import csv
import html
import io
from datetime import date, datetime, timezone

GENERIC_KEY = "(unlinked discussion)"


def _local_dt(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()  # to the machine's local timezone


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


def collect(repo, d_from: date, d_to: date) -> dict:
    """Build the MoM report model for [d_from, d_to] inclusive (local days)."""
    events: list[dict] = []

    for c in repo.all_comments():
        dt = _local_dt(c.get("created_at"))
        if dt is None or not (d_from <= dt.date() <= d_to):
            continue
        gap = repo.get_gap(c["gap_id"]) if c.get("gap_id") else None
        events.append({
            "kind": "comment",
            "when": c.get("created_at"),
            "ts": dt,
            "author": c.get("author") or "—",
            "text": c.get("body") or "",
            "is_reply": bool(c.get("parent_comment_id")),
            "is_number": (gap.is_number if gap else None) or c.get("is_anchor"),
            "gap_type": gap.gap_type.value if gap else None,
            "mapping_context": (gap.mapping_context.value if gap and gap.mapping_context
                                else c.get("mapping_context")),
            "path": gap.v1_path if gap else None,
            "detail": gap.detail if gap else None,
        })

    for h in repo.all_status_changes():
        dt = _local_dt(h.get("changed_at"))
        if dt is None or not (d_from <= dt.date() <= d_to):
            continue
        gap = repo.get_gap(h["gap_id"]) if h.get("gap_id") else None
        events.append({
            "kind": "decision",
            "when": h.get("changed_at"),
            "ts": dt,
            "author": h.get("author") or "—",
            "old_status": h.get("old_status"),
            "new_status": h.get("new_status"),
            "note": h.get("note"),
            "is_number": gap.is_number if gap else None,
            "gap_type": gap.gap_type.value if gap else None,
            "mapping_context": gap.mapping_context.value if gap and gap.mapping_context else None,
            "path": gap.v1_path if gap else None,
            "detail": gap.detail if gap else None,
        })

    events.sort(key=lambda e: e["when"] or "")

    # group by attribute (IS), preserving first-seen order
    groups: dict[str, dict] = {}
    for e in events:
        key = e["is_number"] or GENERIC_KEY
        g = groups.setdefault(key, {
            "is_number": e["is_number"],
            "path": None, "detail": None, "events": [],
        })
        g["events"].append(e)
        if e.get("path") and not g["path"]:
            g["path"] = e["path"]
        if e.get("detail") and not g["detail"]:
            g["detail"] = e["detail"]

    attributes = sorted(groups.values(), key=lambda g: (g["is_number"] is None, g["is_number"] or ""))
    decisions = [e for e in events if e["kind"] == "decision"]
    comments = [e for e in events if e["kind"] == "comment"]
    participants = sorted({e["author"] for e in events if e["author"] and e["author"] != "—"})

    return {
        "from": d_from.isoformat(),
        "to": d_to.isoformat(),
        "generated_at": _fmt(datetime.now(timezone.utc).astimezone()),
        "totals": {
            "decisions": len(decisions),
            "comments": len(comments),
            "attributes": len(attributes),
            "participants": len(participants),
        },
        "participants": participants,
        "attributes": attributes,
        "decisions": decisions,
        "events": events,
    }


# --- helpers ------------------------------------------------------------------

def _label(e: dict) -> str:
    bits = []
    if e.get("gap_type"):
        bits.append(e["gap_type"].split("_")[0])  # G1, G3, ...
    if e.get("mapping_context"):
        bits.append(e["mapping_context"])
    return " · ".join(bits)


def _decision_text(e: dict) -> str:
    old = e.get("old_status") or "—"
    return f"{old} → {e.get('new_status') or '—'}"


def filename(report: dict, ext: str) -> str:
    return f"MoM_{report['from']}_to_{report['to']}.{ext}"


# --- Markdown -----------------------------------------------------------------

def render_markdown(report: dict) -> str:
    t = report["totals"]
    out: list[str] = []
    out.append("# Minutes of Meeting — V2.1 → V1 Schema Conversion")
    out.append("")
    out.append(f"**Period:** {report['from']} → {report['to']}  ")
    out.append(f"**Generated:** {report['generated_at']}  ")
    if report["participants"]:
        out.append(f"**Participants:** {', '.join(report['participants'])}  ")
    out.append(
        f"**Summary:** {t['decisions']} decision(s) · {t['comments']} comment(s) "
        f"across {t['attributes']} attribute(s)."
    )
    out.append("")

    if not report["events"]:
        out.append("_No changes or comments were recorded in this period._")
        return "\n".join(out)

    if report["decisions"]:
        out.append("## Decisions")
        out.append("")
        out.append("| Attribute (IS) | Gap | Decision | By | When | Note |")
        out.append("|---|---|---|---|---|---|")
        for e in report["decisions"]:
            out.append(
                f"| {e['is_number'] or '—'} | {_label(e) or '—'} | {_decision_text(e)} "
                f"| {e['author']} | {_fmt(e['ts'])} | {(e.get('note') or '').replace('|', '/')} |"
            )
        out.append("")

    out.append("## Discussion by attribute")
    out.append("")
    for g in report["attributes"]:
        head = g["is_number"] or GENERIC_KEY
        out.append(f"### {head}")
        if g.get("path"):
            out.append(f"_{g['path']}_  ")
        if g.get("detail"):
            out.append(f"{g['detail']}")
        out.append("")
        for e in g["events"]:
            tag = _label(e)
            tag = f" _({tag})_" if tag else ""
            if e["kind"] == "decision":
                note = f" — {e['note']}" if e.get("note") else ""
                out.append(f"- **{_fmt(e['ts'])}** · {e['author']} set status **{_decision_text(e)}**{tag}{note}")
            else:
                reply = "↳ " if e["is_reply"] else ""
                out.append(f"- **{_fmt(e['ts'])}** · {e['author']}{tag}: {reply}{e['text']}")
        out.append("")

    return "\n".join(out)


# --- CSV ----------------------------------------------------------------------

def render_csv(report: dict) -> str:
    """One row per attribute; all of that attribute's comments collapsed into a
    single comma-separated cell (decisions joined too), for a compact MoM sheet."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["attribute_is", "path", "detail", "gaps", "decisions",
                "comments", "participants"])
    for g in report["attributes"]:
        evs = g["events"]
        comments = [e for e in evs if e["kind"] == "comment"]
        decisions = [e for e in evs if e["kind"] == "decision"]
        gaps = sorted({e["gap_type"].split("_")[0] for e in evs if e.get("gap_type")})
        participants = sorted({e["author"] for e in evs if e["author"] and e["author"] != "—"})

        comment_cell = ", ".join(
            e["text"].strip() for e in comments if e.get("text")
        )
        decision_cell = " | ".join(
            f"{_decision_text(e)} ({e['author']}"
            + (f": {e['note']}" if e.get("note") else "")
            + ")"
            for e in decisions
        )
        w.writerow([
            g["is_number"] or GENERIC_KEY,
            g.get("path") or "",
            g.get("detail") or "",
            ", ".join(gaps),
            decision_cell,
            comment_cell,
            ", ".join(participants),
        ])
    return buf.getvalue()


# --- HTML (the default; styled, print/email friendly) -------------------------

def render_html(report: dict) -> str:
    t = report["totals"]
    esc = html.escape

    def chip(text: str) -> str:
        return f'<span class="chip">{esc(text)}</span>' if text else ""

    parts: list[str] = []
    parts.append(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MoM — V2.1→V1 Schema Conversion · {esc(report['from'])} to {esc(report['to'])}</title>
<style>
  :root {{ --ink:#0f172a; --muted:#64748b; --line:#e2e8f0; --brand:#4f46e5; --soft:#f8fafc; }}
  * {{ box-sizing:border-box; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
         color:var(--ink); margin:0; background:#fff; line-height:1.5; }}
  .wrap {{ max-width:900px; margin:0 auto; padding:40px 28px 64px; }}
  h1 {{ font-size:22px; margin:0 0 4px; letter-spacing:-.01em; }}
  h2 {{ font-size:15px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted);
        margin:34px 0 12px; border-bottom:1px solid var(--line); padding-bottom:6px; }}
  .sub {{ color:var(--muted); font-size:13px; }}
  .cards {{ display:flex; gap:12px; flex-wrap:wrap; margin:18px 0 4px; }}
  .card {{ flex:1; min-width:130px; border:1px solid var(--line); border-radius:14px; padding:14px 16px; background:var(--soft); }}
  .card .n {{ font-size:26px; font-weight:700; }}
  .card .l {{ font-size:11px; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; margin-top:6px; }}
  th, td {{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  th {{ color:var(--muted); font-weight:600; background:var(--soft); }}
  .attr {{ border:1px solid var(--line); border-radius:14px; padding:16px 18px; margin:14px 0; }}
  .attr h3 {{ margin:0; font-size:16px; }}
  .attr .path {{ color:var(--muted); font-size:12px; margin:2px 0 2px; }}
  .attr .detail {{ color:#334155; font-size:13px; margin:4px 0 10px; }}
  .ev {{ display:flex; gap:10px; padding:8px 0; border-top:1px dashed var(--line); }}
  .ev:first-of-type {{ border-top:none; }}
  .ev .t {{ color:var(--muted); font-size:12px; min-width:118px; white-space:nowrap; }}
  .ev .who {{ font-weight:600; }}
  .ev.reply .body {{ margin-left:14px; border-left:2px solid var(--line); padding-left:10px; }}
  .pill {{ display:inline-block; font-size:11px; font-weight:600; padding:1px 8px; border-radius:999px;
           background:#eef2ff; color:var(--brand); }}
  .pill.dec {{ background:#ecfdf5; color:#047857; }}
  .chip {{ display:inline-block; font-size:11px; color:var(--muted); background:var(--soft);
           border:1px solid var(--line); border-radius:999px; padding:0 7px; margin-left:6px; }}
  .empty {{ color:var(--muted); font-style:italic; padding:24px 0; }}
  .foot {{ margin-top:40px; color:#94a3b8; font-size:11px; border-top:1px solid var(--line); padding-top:12px; }}
  @media print {{ .wrap {{ padding:0; }} .card {{ background:#fff; }} }}
</style></head><body><div class="wrap">""")

    parts.append("<h1>Minutes of Meeting — V2.1 → V1 Schema Conversion</h1>")
    parts.append(f'<div class="sub">Period <strong>{esc(report["from"])}</strong> to '
                 f'<strong>{esc(report["to"])}</strong> · generated {esc(report["generated_at"])}</div>')
    if report["participants"]:
        parts.append(f'<div class="sub">Participants: {esc(", ".join(report["participants"]))}</div>')

    parts.append('<div class="cards">')
    for n, lbl in [(t["decisions"], "Decisions"), (t["comments"], "Comments"),
                   (t["attributes"], "Attributes"), (t["participants"], "Participants")]:
        parts.append(f'<div class="card"><div class="n">{n}</div><div class="l">{lbl}</div></div>')
    parts.append("</div>")

    if not report["events"]:
        parts.append('<p class="empty">No changes or comments were recorded in this period.</p>')
        parts.append(_html_footer())
        return "".join(parts)

    # Decisions table
    if report["decisions"]:
        parts.append("<h2>Decisions</h2>")
        parts.append("<table><thead><tr><th>Attribute</th><th>Gap</th><th>Decision</th>"
                     "<th>By</th><th>When</th><th>Note</th></tr></thead><tbody>")
        for e in report["decisions"]:
            parts.append(
                "<tr>"
                f"<td><strong>{esc(e['is_number'] or '—')}</strong></td>"
                f"<td>{esc(_label(e) or '—')}</td>"
                f"<td><span class='pill dec'>{esc(_decision_text(e))}</span></td>"
                f"<td>{esc(e['author'])}</td>"
                f"<td>{esc(_fmt(e['ts']))}</td>"
                f"<td>{esc(e.get('note') or '')}</td>"
                "</tr>"
            )
        parts.append("</tbody></table>")

    # Discussion grouped by attribute
    parts.append("<h2>Discussion by attribute</h2>")
    for g in report["attributes"]:
        parts.append('<div class="attr">')
        parts.append(f"<h3>{esc(g['is_number'] or GENERIC_KEY)}</h3>")
        if g.get("path"):
            parts.append(f'<div class="path">{esc(g["path"])}</div>')
        if g.get("detail"):
            parts.append(f'<div class="detail">{esc(g["detail"])}</div>')
        for e in g["events"]:
            reply = " reply" if (e["kind"] == "comment" and e["is_reply"]) else ""
            parts.append(f'<div class="ev{reply}"><div class="t">{esc(_fmt(e["ts"]))}</div><div class="body">')
            if e["kind"] == "decision":
                note = f" — {esc(e['note'])}" if e.get("note") else ""
                parts.append(f'<span class="who">{esc(e["author"])}</span> '
                             f'<span class="pill dec">status {esc(_decision_text(e))}</span>'
                             f'{chip(_label(e))}{note}')
            else:
                parts.append(f'<span class="who">{esc(e["author"])}</span> '
                             f'<span class="pill">comment</span>{chip(_label(e))}'
                             f'<div>{esc(e["text"])}</div>')
            parts.append("</div></div>")
        parts.append("</div>")

    parts.append(_html_footer())
    return "".join(parts)


def _html_footer() -> str:
    return ('<div class="foot">Generated by the V2.1→V1 Gap Analysis Dashboard · '
            'MoM export. Times shown in the local timezone.</div></div></body></html>')
