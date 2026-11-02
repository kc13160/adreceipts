"""drill: prove that undo works on this phone before any real change.

1. Pick a harmless package from the drill list (not protected, no role, not on screen).
2. Disable it and read the state back.
3. Enable it again and read the state back.
4. Write drill.json, tied to this phone and system build.
apply --execute refuses to run without it. There is no flag to skip it.
"""

from __future__ import annotations

from . import device, guard, ops
from .errors import RunStopped, SafetyStop
from .journal import Journal
from .store import now_iso, read_json, require_same_device, write_json

SCAN_ONLY = "You can still use AdReceipts in scan-only mode: python adreceipts.py scan"


def choose(cat, states, held, fg):
    rejected = []
    for cand in cat.drill_candidates:
        name = cand["name"]
        st = states.get(name)
        if not st:
            continue
        if st["state"] != "enabled":
            rejected.append("%s: not enabled" % name)
            continue
        d = guard.check_package(name, cat, held, purpose="drill", foreground=fg)
        if not d:
            rejected.append("%s: %s" % (name, "; ".join(d.reasons)))
            continue
        return cand, rejected
    return None, rejected


def run(app):
    adb = app.connect("write")
    props, dev, run_id, run_dir = app.run_for_device(adb)
    backup = read_json(run_dir / "backup.json")
    if not backup:
        raise SafetyStop("No backup in this run. The drill comes after the backup.",
                         hint="Run: python adreceipts.py backup")
    require_same_device(backup.get("device"), dev, "backup")
    cat = app.catalog(props)
    rules = cat.drill_rules or {}
    states = device.package_states(adb)
    role_map = device.roles(adb)
    held = device.role_holders(role_map)
    fg = device.foreground(adb)
    cand, rejected = choose(cat, states, held, fg)
    result = {"time": now_iso(), "run_id": run_id, "device": dev, "passed": False, "steps": []}
    if cand is None:
        result["reason"] = "no safe drill candidate on this phone"
        result["rejected"] = rejected
        write_json(run_dir / "drill.json", result)
        raise SafetyStop("No harmless package on this phone can be used for the undo drill, so no change will be made.",
                         hint=SCAN_ONLY)

    name = cand["name"]
    journal = Journal(run_dir)
    ctx = ops.Context(adb, journal, app.sleep, settle=float(rules.get("settle_seconds", 1)),
                      attempts=int(rules.get("readback_attempts", 3)))
    app.say("Undo drill with %s (%s)" % (name, cand["reason"]))
    status, detail = ops.change_package(ctx, "drill", name, "disable")
    result["package"] = name
    result["steps"].append({"step": "disable", "status": status, "detail": detail})
    app.say("  1. disable: %s (%s)" % (status, detail))
    if status != "done":
        failures = ops.undo_batch(ctx, "drill")
        result["undo_failures"] = failures
        write_json(run_dir / "drill.json", result)
        msg = "The drill could not disable %s (%s). Nothing else will be changed." % (name, detail)
        if failures:
            msg += " Putting it back also failed: %s" % "; ".join(failures)
        raise RunStopped(msg, hint=SCAN_ONLY)

    change = journal.open_changes(batch="drill")[0]
    ok, detail = ops.reverse(ctx, change, "undone")
    result["steps"].append({"step": "enable", "status": "done" if ok else "failed", "detail": detail})
    app.say("  2. enable again: %s (%s)" % ("done" if ok else "failed", detail))
    final = device.package_state(adb, name)
    result["final_state"] = final["state"]
    journal.write_scripts()
    if not ok or final["state"] != "enabled":
        write_json(run_dir / "drill.json", result)
        raise RunStopped(
            "Undo did not work on this phone: %s is %s. No other change will be made." % (name, final["state"]),
            hint="Re-enable it by hand: Settings > Apps > show system apps > %s > Enable. "
                 "Or run restore-standalone in %s. %s" % (name, run_dir, SCAN_ONLY))
    result["passed"] = True
    write_json(run_dir / "drill.json", result)
    app.say("Drill passed: change and undo both verified on this phone.", "", "Next: python adreceipts.py plan")
    return 0
