"""backup: save the current state and write the standalone restore scripts."""

from __future__ import annotations

from . import device
from .journal import Journal
from .store import now_iso, write_json


def run(app):
    adb = app.connect("read")
    props, dev, run_id, run_dir = app.run_for_device(adb)
    app.need(run_dir, "scan.json", "Run scan first: python adreceipts.py scan")
    cat = app.catalog(props)
    states = device.package_states(adb)
    watched = sorted(set(cat.packages) | {d["name"] for d in cat.drill_candidates})
    settings = {}
    for s in cat.surfaces.values():
        st = s["turn_off"].get("setting")
        if st:
            settings["%s/%s" % (st["namespace"], st["key"])] = device.setting(adb, st["namespace"], st["key"])
    for ns, key in (("global", "private_dns_mode"), ("global", "private_dns_specifier")):
        settings["%s/%s" % (ns, key)] = device.setting(adb, ns, key)
    data = {
        "time": now_iso(),
        "run_id": run_id,
        "device": dev,
        "packages": {n: states[n] for n in watched if n in states},
        "settings": settings,
        "roles": device.roles(adb),
    }
    write_json(run_dir / "backup.json", data)
    journal = Journal(run_dir)
    journal.write_scripts()
    app.say("Backup saved. Nothing was changed on the phone.",
            "  %s" % (run_dir / "backup.json"),
            "Standalone restore scripts (they only undo what AdReceipts records later):",
            "  %s" % (run_dir / "restore-standalone.sh"),
            "  %s" % (run_dir / "restore-standalone.cmd"),
            "", "Next: python adreceipts.py drill")
    return 0
