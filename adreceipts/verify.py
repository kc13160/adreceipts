"""verify: automatic health checks plus a checklist the user confirms by hand."""

from __future__ import annotations

from . import device, ops
from .store import now_iso, read_json, write_json

CHECKLIST = {
    "calls": "Make a short phone call and receive one.",
    "sms": "Send and receive a text message (SMS).",
    "notifications": "Receive a notification from an app you use (for example a message app).",
    "payments": "Open your banking and payment apps; if you pay by phone (NFC), check it is still ready.",
}


def run(app):
    args = app.args
    adb = app.connect("read")
    props, dev, run_id, run_dir = app.run_for_device(adb, check_build=False)
    role_map = device.roles(adb)
    baseline = ops.health_baseline(adb, role_map)
    baseline["systemui_pid"] = None
    problems = ops.health_check(adb, baseline, app.sleep)

    old = read_json(run_dir / "verify.json") or {}
    confirmed = sorted(set(old.get("confirmed", [])) | set(args.confirmed))
    record = {"time": now_iso(), "automatic_problems": problems, "confirmed": confirmed,
              "problems_reported": old.get("problems_reported", [])}
    if args.problem:
        record["problems_reported"].append({"time": now_iso(), "text": args.problem[:500]})
    write_json(run_dir / "verify.json", record)

    app.say("Automatic checks (read-only):")
    if problems:
        for p in problems:
            app.say("  [PROBLEM] %s" % p)
    else:
        app.say("  [OK] phone reachable, fully started, home screen running, System UI running, phone and SMS apps enabled")
    app.say("", "Please check these by hand on the phone:")
    for key, text in CHECKLIST.items():
        app.say("  [%s] %s: %s" % ("x" if key in confirmed else " ", key, text))
    missing = [k for k in CHECKLIST if k not in confirmed]
    if missing:
        app.say("", "When a check works, record it: python adreceipts.py verify --confirmed %s" % " ".join(missing))
    if problems or args.problem:
        app.say("", "Something is wrong. Undo everything with: python adreceipts.py restore --all",
                "or undo one batch with: python adreceipts.py restore --batch <ID>")
        return 1
    app.say("", "Next: python adreceipts.py receipts")
    return 0
