"""plan: choices grouped by surface, in plain words, with risk and side effects.

Only entries that are both "safe" and "tested" are pre-selected. Everything
else needs to be selected item by item, with an extra warning. Approval is
stored with a hash of the exact selection; any change clears it.
plan reads the phone only.
"""

from __future__ import annotations

import hashlib
import json

from . import device, guard, report
from .errors import AdReceiptsError
from .store import now_iso, read_json, write_json

DNS_WARNING = ("Private DNS sends every domain name your phone looks up to the provider you choose. "
               "It blocks some ad domains, not all ads, and it can block things you want.")


def selection_hash(items):
    core = [{k: it.get(k) for k in ("id", "kind", "target", "namespace", "key", "value")} for it in items]
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode("utf-8")).hexdigest()


def build_items(cat, states, held, settings_now):
    items, refused = [], []
    for name, entry in sorted(cat.packages.items()):
        st = states.get(name)
        if not st or st["state"] != "enabled":
            continue
        d = guard.check_package(name, cat, held, method="disable")
        item = {
            "id": "pkg:" + name, "kind": "package", "target": name, "title": entry["role"],
            "category": entry["category"], "risk": entry["risk"], "proof": entry["proof"],
            "side_effects": entry["side_effects"], "source": entry["source"],
            "surfaces": entry.get("surfaces", []),
            "preselected": bool(d) and entry["risk"] == "safe" and entry["proof"] == "tested",
        }
        if d:
            items.append(item)
        else:
            item["refused"] = d.reasons
            refused.append(item)
    for sid, s in sorted(cat.surfaces.items()):
        st = s["turn_off"].get("setting")
        if not st:
            continue
        value = settings_now.get(sid)
        if value is None or value not in st["on_values"]:
            continue
        d = guard.check_setting(st["namespace"], st["key"], st["off_value"], cat)
        item = {
            "id": "set:" + sid, "kind": "setting", "target": "%s/%s" % (st["namespace"], st["key"]),
            "namespace": st["namespace"], "key": st["key"], "value": st["off_value"], "title": s["name"],
            "risk": s["risk"], "proof": s["proof"], "side_effects": s["side_effects"], "source": s["source"],
            "surfaces": [sid], "preselected": bool(d) and s["risk"] == "safe" and s["proof"] == "tested",
        }
        (items if d else refused).append(item if d else dict(item, refused=d.reasons))
    return items, refused


def manual_steps(cat):
    out = []
    for sid, s in cat.surfaces.items():
        if s["turn_off"]["method"] == "manual":
            out.append({"id": sid, "name": s["name"], "steps": s["turn_off"]["steps"], "source": s["source"],
                        "side_effects": s["side_effects"], "proof": s["proof"]})
    return out


def dns_item(cat, provider, host):
    if provider == "custom":
        if not host or not guard.check_hostname(host):
            raise AdReceiptsError("--dns custom needs a valid --dns-host, for example dns.example.org")
        name, source = "Your own Private DNS host", ""
    else:
        p = cat.dns_providers.get(provider)
        if not p:
            raise AdReceiptsError("Unknown DNS provider %r." % provider,
                                  hint="Choose one of: %s, or custom" % ", ".join(sorted(cat.dns_providers)))
        host, name, source = p["hostname"], p["name"], p["source"]
    return {"id": "dns", "kind": "dns", "target": host, "title": "Private DNS: %s (%s)" % (name, host),
            "risk": "prudent", "proof": "documented", "side_effects": DNS_WARNING, "source": source,
            "surfaces": [], "preselected": False}


def build_doc(plan, cat, dev):
    def rows(items):
        out = []
        for it in items:
            out.append([{"code": it["id"]}, "yes" if it["id"] in plan["selected"] else "no", it["title"], it["risk"],
                        it["proof"], it["side_effects"]])
        return out

    sections = [{"h": "Summary", "blocks": [
        {"p": "Phone: %s. Run: %s." % (report.device_line(dev), plan["run_id"])},
        {"note": "Only entries rated safe and tested on a real device are pre-selected. Nothing in the catalog is "
                 "tested yet, so nothing is pre-selected: choose each item yourself."},
        {"p": "Approved: %s" % ("yes, at %s" % plan["approved"]["time"] if plan.get("approved") else "not yet")},
    ]}]
    sections.append({"h": "Changes AdReceipts can make (only after approval)", "blocks": [
        {"table": {"head": ["ID", "Selected", "What it is", "Risk", "Proof", "Side effects"], "rows": rows(plan["items"])}}]})
    if plan.get("refused"):
        sections.append({"h": "Not offered (refused by guard)", "blocks": [{"table": {
            "head": ["Package", "What it is", "Why not"],
            "rows": [[{"code": it["target"]}, it["title"], "; ".join(it["refused"])] for it in plan["refused"]]}}]})
    if plan.get("manual"):
        blocks = [{"p": "These switches are inside the phone's menus. Turn them off by hand; AdReceipts does not tap for you."}]
        for m in plan["manual"]:
            blocks.append({"p": "%s (%s):" % (m["name"], m["proof"])})
            blocks.append({"ul": m["steps"]})
        sections.append({"h": "Switches to turn off by hand", "blocks": blocks})
    sections.append({"h": "Private DNS (optional)", "blocks": [
        {"p": DNS_WARNING},
        {"ul": ["%s: %s (%s) - %s" % (p["id"], p["name"], p["hostname"], p["source"]) for p in cat.dns_providers.values()]
               + ["custom: your own provider hostname"]},
        {"p": "Add it with: python adreceipts.py plan --dns <id>   (or --dns custom --dns-host HOST)"},
    ]})
    sections.append({"h": "What this does not promise", "blocks": [{"ul": report.LIMITS}]})
    return {"title": "AdReceipts plan", "subtitle": now_iso(), "simulated": dev.get("simulated"), "sections": sections}


def run(app):
    args = app.args
    adb = app.connect("read")
    props, dev, run_id, run_dir = app.run_for_device(adb)
    app.need(run_dir, "scan.json", "Run scan first: python adreceipts.py scan")
    cat = app.catalog(props)
    states = device.package_states(adb)
    held = device.role_holders(device.roles(adb))
    settings_now = {}
    for sid, s in cat.surfaces.items():
        st = s["turn_off"].get("setting")
        if st:
            settings_now[sid] = device.setting(adb, st["namespace"], st["key"])
    items, refused = build_items(cat, states, held, settings_now)

    old = read_json(run_dir / "plan.json") or {}
    old_dns = next((i for i in old.get("items", []) if i["kind"] == "dns"), None)
    if args.no_dns:
        old_dns = None
    if args.dns:
        old_dns = dns_item(cat, args.dns, args.dns_host)
    if old_dns:
        items.append(old_dns)
    ids = {i["id"] for i in items}
    if "selected" in old:
        selected = [i for i in old["selected"] if i in ids]
    else:
        selected = [i["id"] for i in items if i["preselected"]]
    if args.dns and "dns" not in selected:
        selected.append("dns")

    warnings = []
    for sel in args.select:
        if sel not in ids:
            hint = "It was refused by guard: see the plan report." if any(r["id"] == sel for r in refused) else \
                "Check the IDs in the plan report."
            raise AdReceiptsError("%s cannot be selected." % sel, hint=hint)
        if sel not in selected:
            selected.append(sel)
        item = next(i for i in items if i["id"] == sel)
        if not item["preselected"]:
            warnings.append("%s is %s and %s (not tested on a real device). Side effects: %s" % (
                sel, item["risk"], item["proof"], item["side_effects"]))
    for sel in args.deselect:
        if sel in selected:
            selected.remove(sel)

    chosen = [i for i in items if i["id"] in selected]
    approved = old.get("approved")
    if approved and (approved.get("hash") != selection_hash(chosen) or approved.get("device") != dev.get("id_hash")):
        approved = None
    if args.select or args.deselect or args.dns or args.no_dns:
        approved = None
    if args.approve:
        if not chosen:
            raise AdReceiptsError("Nothing is selected, so there is nothing to approve.",
                                  hint="Select items first: python adreceipts.py plan --select <ID>")
        approved = {"time": now_iso(), "hash": selection_hash(chosen), "device": dev.get("id_hash"),
                    "build": dev.get("build_hash"), "items": [i["id"] for i in chosen]}

    plan = {"run_id": run_id, "time": now_iso(), "device": dev, "items": items, "refused": refused,
            "manual": manual_steps(cat), "selected": selected, "approved": approved,
            "warnings": old.get("warnings", []) + warnings}
    write_json(run_dir / "plan.json", plan)
    path = report.write(build_doc(plan, cat, dev), run_dir, "plan")

    app.say("Plan (nothing on the phone was changed).", "")
    for it in items:
        mark = "[x]" if it["id"] in selected else "[ ]"
        app.say("%s %-45s %-9s %-10s %s" % (mark, it["id"], it["risk"], it["proof"], it["title"]))
    for it in refused:
        app.say("[-] %-45s refused: %s" % (it["id"], "; ".join(it["refused"])))
    for w in warnings:
        app.say("", "WARNING: " + w)
    if plan["manual"]:
        app.say("", "%d switches must be turned off by hand: see the plan report." % len(plan["manual"]))
    app.say("", "Report: %s" % path)
    if approved:
        app.say("Approved %d item(s). Next: python adreceipts.py apply   (dry run first)" % len(chosen))
    else:
        app.say("Not approved yet. Select with --select <ID>, then approve with --approve.")
    return 0
