"""scan: find ad sources. Read-only. Screen evidence only with --screenshots --consent."""

from __future__ import annotations

import re

from . import device, evidence, report, screen
from .store import now_iso, write_json


def coverage_note(cat, dev, props):
    """Say plainly when this system version is not one the catalog sources describe."""
    name = props.get("ro.mi.os.version.name") or ""
    m = re.match(r"OS(\d+)", name)
    versions = cat.system_versions()
    if m:
        label = "HyperOS %s" % m.group(1)
        if label not in versions:
            return ("Your system (%s) is not one of the versions the catalog sources describe (%s). "
                    "Menu names and ad locations may differ." % (label, ", ".join(versions)))
    return None


def surface_rows(cat, ev):
    rows = []
    for sid, s in cat.surfaces.items():
        info = ev["surfaces"].get(sid, {})
        if not info.get("present", True):
            continue
        how = s["turn_off"]["method"]
        how_text = {"manual": "by hand in the phone's menus", "package": "turn off the app that serves it",
                    "setting": "a phone setting"}[how]
        rows.append([s["name"], {"badges": info.get("labels", [])}, "; ".join(info.get("details", [])) or "-",
                     how_text, s["proof"]])
    return rows


def package_rows(ev):
    rows = []
    for name, p in sorted(ev["packages"].items()):
        label = evidence.SERVICE_ACTIVE if p["state"] == "enabled" else evidence.NOT_SEEN
        rows.append([{"code": name}, p["role"], p["state"], {"badges": [label]}, p["risk"], p["proof"]])
    return rows


def build_doc(dev, props, cat, ev, screenshots, run_id):
    note = coverage_note(cat, dev, props)
    intro = [
        {"p": "Phone: %s." % report.device_line(dev)},
        {"p": "Catalog used: %s. Run: %s." % (", ".join(cat.labels), run_id)},
        {"note": "Nothing was changed on the phone. scan only reads. You can stop here."},
    ]
    if note:
        intro.append({"note": note})
    surfaces = [
        {"p": "Each place where ads can appear, and what was found. Labels say only what was observed."},
        {"table": {"head": ["Location", "Found", "Details", "How it is turned off", "Proof level"],
                   "rows": surface_rows(cat, ev)}},
    ]
    if not screenshots:
        surfaces.append({"p": "Screens were not opened (screenshots are off by default), so most locations are 'not checked'."})
    sections = [
        {"h": "Summary", "blocks": intro},
        {"h": "Ad locations", "blocks": surfaces},
        {"h": "Ad and tracking packages found", "blocks": [
            {"table": {"head": ["Package", "What it is", "State", "Label", "Risk", "Proof"], "rows": package_rows(ev)}}]},
    ]
    if ev["absent"]:
        sections.append({"h": "Catalog packages not on this phone", "blocks": [{"ul": ev["absent"]}]})
    info_rows = []
    for chk in cat.info_checks:
        value = ev["info"].get(chk["id"])
        info_rows.append([chk["name"], value if value is not None else "not set", chk["explain"]])
    if info_rows:
        sections.append({"h": "Phone settings read", "blocks": [{"table": {"head": ["Setting", "Value", "Meaning"], "rows": info_rows}}]})
    if ev["unknown_adlike"]:
        sections.append({"h": "Unrecognized packages with ad-like names", "blocks": [
            {"p": "These are not in the catalog. They are reported only and never offered for action."},
            {"ul": ev["unknown_adlike"]}]})
    sections.append({"h": "What this report does not prove", "blocks": [{"ul": report.LIMITS}]})
    sections.append({"h": "Next steps", "blocks": [{"ul": [
        "Stop here if you only wanted to look. Nothing was changed.",
        "To continue: python adreceipts.py backup, then drill, then plan.",
    ]}]})
    return {"title": "AdReceipts scan", "subtitle": "%s - %s" % (report.device_line(dev), now_iso()),
            "simulated": dev.get("simulated"), "sections": sections}


def run(app):
    args = app.args
    if args.screenshots and not args.consent:
        app.say(screen.CONSENT_TEXT)
        return 2
    adb = app.connect("screen" if args.screenshots else "read")
    props, dev = device.identity(adb, app.home)
    cat = app.catalog(props)
    run_id, run_dir = app.runs.new(dev)
    screens = evidence.capture_all(adb, cat, run_dir, "before", app.sleep) if args.screenshots else {}
    ev = evidence.collect(adb, cat, screens)
    write_json(run_dir / "scan.json", {
        "time": now_iso(), "device": dev, "catalogs": cat.labels, "screenshots": bool(args.screenshots), "evidence": ev,
    })
    doc = build_doc(dev, props, cat, ev, args.screenshots, run_id)
    path = report.write(doc, run_dir, "scan")

    active = [n for n, p in ev["packages"].items() if p["state"] == "enabled"]
    app.say("Scan finished. Nothing was changed on the phone.",
            "Phone: %s" % report.device_line(dev),
            "Ad or tracking packages switched on: %d" % len(active))
    for n in active:
        app.say("  - %s (%s)" % (n, ev["packages"][n]["role"]))
    seen = [sid for sid, s in ev["surfaces"].items() if evidence.AD_SEEN in s["labels"]]
    if args.screenshots:
        app.say("Screens with ad words seen: %d" % len(seen))
    if ev["unknown_adlike"]:
        app.say("Unrecognized ad-like packages (reported only): %d" % len(ev["unknown_adlike"]))
    app.say("Report: %s" % path, "Run: %s" % run_id, "",
            "You can stop here. To continue: python adreceipts.py backup")
    return 0
