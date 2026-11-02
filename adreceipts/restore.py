"""restore: reverse only what the journal recorded, newest first.

Packages that were already off before AdReceipts ran are never touched.
"""

from __future__ import annotations

from . import device, ops
from .errors import AdReceiptsError, RunStopped
from .journal import Journal
from .store import read_json, require_same_device


def run(app):
    args = app.args
    if not args.batch and not args.all:
        raise AdReceiptsError("Say what to restore: --batch ID or --all.",
                              hint="See the batch IDs in apply's output or in journal.jsonl.")
    adb = app.connect("write")
    props, dev = device.identity(adb, app.home)
    run_id, run_dir = app.run()
    saved = (read_json(run_dir / "run.json") or {}).get("device")
    # Same phone required. A system update in between is allowed: restoring after an update is normal.
    require_same_device(saved, dev, "run %s" % run_id, check_build=False)
    journal = Journal(run_dir)
    if args.batch and args.batch not in journal.batches():
        raise AdReceiptsError("Batch %s is not in this run's journal." % args.batch,
                              hint="Batches recorded: %s" % (", ".join(journal.batches()) or "none"))
    todo = journal.open_changes(batch=args.batch if args.batch else None)
    if not todo:
        journal.write_scripts()
        app.say("Nothing to restore: every recorded change is already undone.")
        return 0
    ctx = ops.Context(adb, journal, app.sleep)
    failures = []
    for change in todo:
        ok, detail = ops.reverse(ctx, change, "restored")
        app.say("  %-8s %-45s %s" % ("ok" if ok else "FAILED", change["target"], detail))
        if not ok:
            failures.append("%s (%s)" % (change["target"], detail))
    journal.write_scripts()
    if failures:
        raise RunStopped("Some changes could not be undone: %s" % "; ".join(failures),
                         hint="Re-enable them by hand: Settings > Apps > show system apps > the app > Enable. "
                              "Then run: python adreceipts.py recheck")
    app.say("", "Restored %d change(s). Next: python adreceipts.py recheck" % len(todo))
    return 0
