"""restore: reverse only what the journal recorded, newest first.

Packages that were already off before AdReceipts ran are never touched.
Without --run, every run made on this phone is searched, so a later scan
(which starts a new run) does not hide earlier changes.
"""

from __future__ import annotations

from . import device, guard, ops
from .errors import AdReceiptsError, RunStopped, SafetyStop
from .journal import Journal
from .store import read_json, require_same_device


def runs_for_device(app, dev):
    """Runs made on this phone, newest first."""
    out = []
    for run_id in reversed(app.runs.all()):
        saved = (read_json(app.home / run_id / "run.json") or {}).get("device")
        if saved and saved.get("id_hash") == dev.get("id_hash"):
            out.append(run_id)
    return out


def allowed(change, cat):
    """A hand-edited journal must not make restore write a setting guard would refuse."""
    if change["op"] != "setting":
        return True, ""
    d = guard.check_setting(change.get("namespace"), change.get("key"), (change.get("before") or {}).get("value"), cat)
    return bool(d), "; ".join(d.reasons)


def run(app):
    args = app.args
    if not args.batch and not args.all:
        raise AdReceiptsError("Say what to restore: --batch ID or --all.",
                              hint="See the batch IDs in apply's output or in journal.jsonl.")
    adb = app.connect("write")
    props, dev = device.identity(adb, app.home)
    cat = app.catalog(props)

    if args.run:
        run_id, run_dir = app.run()
        saved = (read_json(run_dir / "run.json") or {}).get("device")
        # Same phone required. A system update in between is allowed: restoring after an update is normal.
        require_same_device(saved, dev, "run %s" % run_id, check_build=False)
        candidates = [run_id]
    else:
        candidates = runs_for_device(app, dev)
        if not candidates and app.runs.all():
            raise SafetyStop("The runs in %s were made on another phone." % app.home,
                             hint="Connect the phone the changes were made on.")

    targets = []
    for run_id in candidates:
        journal = Journal(app.home / run_id)
        if args.batch:
            if args.batch in journal.batches():
                targets.append((run_id, journal, journal.open_changes(batch=args.batch)))
                break
        else:
            todo = journal.open_changes()
            if todo:
                targets.append((run_id, journal, todo))
    if args.batch and not targets:
        raise AdReceiptsError("Batch %s was not found in the journals of this phone." % args.batch,
                              hint="Use --run ID to pick a run, or --all.")

    total, failures = 0, []
    for run_id, journal, todo in targets:
        if not todo:
            continue
        app.say("Run %s:" % run_id)
        ctx = ops.Context(adb, journal, app.sleep)
        for change in todo:
            ok, why = allowed(change, cat)
            if ok:
                ok, detail = ops.reverse(ctx, change, "restored")
            else:
                detail = "refused by guard: %s" % why
            app.say("  %-8s %-45s %s" % ("ok" if ok else "FAILED", change["target"], detail))
            total += 1
            if not ok:
                failures.append("%s (%s)" % (change["target"], detail))
        journal.write_scripts()
    if total == 0:
        app.say("Nothing to restore: every change AdReceipts recorded on this phone is already undone.")
        return 0
    if failures:
        raise RunStopped("Some changes could not be undone: %s" % "; ".join(failures),
                         hint="Re-enable them by hand: Settings > Apps > show system apps > the app > Enable. "
                              "Then run: python adreceipts.py recheck")
    app.say("", "Restored %d change(s). Next: python adreceipts.py recheck" % total)
    return 0
