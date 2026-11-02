"""apply: carry out the approved plan, in small batches, with undo on any problem.

Order enforced in code: backup, then a passed drill, then an approved plan,
all for this same phone and system build. Without --execute nothing is sent.
"""

from __future__ import annotations

from . import device, dns, guard, ops
from .errors import AdReceiptsError, RunStopped, SafetyStop
from .journal import Journal
from .plan import selection_hash
from .store import now_iso, read_json, require_same_device, write_json

MAX_BATCH = 5


def make_batches(items):
    """Safe items in groups of at most 5. Anything riskier, and DNS, runs alone."""
    batches, current = [], []
    for it in items:
        if it["kind"] == "dns":
            continue
        if it.get("risk") != "safe":
            batches.append([it])
            continue
        current.append(it)
        if len(current) == MAX_BATCH:
            batches.append(current)
            current = []
    if current:
        batches.append(current)
    batches.extend([it] for it in items if it["kind"] == "dns")
    return batches


def check_order(app, run_dir, run_id, dev):
    backup = read_json(run_dir / "backup.json")
    if not backup:
        raise SafetyStop("No backup for this run. Nothing was changed.", hint="Run: python adreceipts.py backup")
    require_same_device(backup.get("device"), dev, "backup")
    drill = read_json(run_dir / "drill.json")
    if not drill or not drill.get("passed"):
        raise SafetyStop("No passed undo drill for this run. Nothing was changed.",
                         hint="Run: python adreceipts.py drill")
    if drill.get("run_id") != run_id:
        raise SafetyStop("The undo drill belongs to another run. Nothing was changed.", hint="Run the drill again.")
    require_same_device(drill.get("device"), dev, "undo drill")
    plan = read_json(run_dir / "plan.json")
    if not plan or not plan.get("approved"):
        raise SafetyStop("The plan is not approved. Nothing was changed.",
                         hint="Review it with: python adreceipts.py plan, then add --approve")
    chosen = [i for i in plan["items"] if i["id"] in plan["selected"]]
    approved = plan["approved"]
    if approved.get("hash") != selection_hash(chosen) or approved.get("device") != dev.get("id_hash") \
            or approved.get("build") != dev.get("build_hash"):
        raise SafetyStop("The approval does not match the current plan or phone. Nothing was changed.",
                         hint="Approve again: python adreceipts.py plan --approve")
    return plan, chosen


def describe(item, method):
    if item["kind"] == "package":
        if method == "uninstall":
            return "pm uninstall -k --user 0 %s" % item["target"]
        return "pm disable-user --user 0 %s" % item["target"]
    if item["kind"] == "setting":
        return "settings put %s %s %s" % (item["namespace"], item["key"], item["value"])
    return "settings put global private_dns_specifier %s; private_dns_mode hostname; then test name lookups" % item["target"]


def interrupted(app, ctx, batch_id, exc):
    """adb failed or the user pressed Ctrl-C in the middle of a batch: try to undo it, then stop."""
    reason = "interrupted by the user" if isinstance(exc, KeyboardInterrupt) else getattr(exc, "message", str(exc))
    try:
        failures = ops.undo_batch(ctx, batch_id)
        undo = "The batch was undone." if not failures else "Undo was incomplete: %s." % "; ".join(failures)
    except (AdReceiptsError, KeyboardInterrupt, OSError):
        failures = ["not possible right now"]
        undo = "The batch could not be undone right now."
    try:
        ctx.journal.write_scripts()
    except (AdReceiptsError, OSError):
        pass
    raise RunStopped("Stopped in batch %s: %s. %s" % (batch_id, reason, undo),
                     hint="Reconnect the phone, then run: python adreceipts.py restore --all "
                          "(or restore-standalone in the run folder).")


def run(app):
    args = app.args
    method = args.method
    if method == "uninstall" and not args.i_understand_uninstall:
        raise SafetyStop("--method uninstall also needs --i-understand-uninstall. Nothing was changed.",
                         hint="Uninstall for user 0 hides the app; it is restored with 'cmd package install-existing'. "
                              "Only system apps rated safe are allowed.")
    if args.i_understand_uninstall and method != "uninstall":
        raise SafetyStop("--i-understand-uninstall is only used with --method uninstall. Nothing was changed.")

    adb = app.connect("write" if args.execute else "read")
    props, dev, run_id, run_dir = app.run_for_device(adb)
    plan, chosen = check_order(app, run_dir, run_id, dev)
    cat = app.catalog(props)
    states = device.package_states(adb)
    role_map = device.roles(adb)
    if role_map.get("unreadable"):
        raise SafetyStop("Some role holders could not be read (%s), so they cannot be protected. Nothing was changed."
                         % ", ".join(role_map["unreadable"]), hint="Android 10 or newer is needed for changes.")
    if not role_map.get("home"):
        raise SafetyStop("The home screen app could not be read, so health checks are not possible. Nothing was changed.")
    held = device.role_holders(role_map)
    # Every item passes guard before the first write. One refusal stops everything.
    guard.require_batch(chosen, cat, held, method=method, states=states)
    batches = make_batches(chosen)

    if not args.execute:
        app.say("Dry run: nothing will be changed. These batches would run:", "")
        for n, b in enumerate(batches, 1):
            app.say("Batch %d:" % n)
            for it in b:
                app.say("  %s" % describe(it, method))
        app.say("", "After each batch: read-back and health checks; on any problem the batch is undone and the run stops.",
                "To really apply: python adreceipts.py apply --execute")
        return 0

    journal = Journal(run_dir)
    ctx = ops.Context(adb, journal, app.sleep)
    baseline = ops.health_baseline(adb, role_map)
    done_batches = [b for b in journal.batches() if b.isdigit()]
    next_no = max([int(b) for b in done_batches] or [0]) + 1
    summary = {"time": now_iso(), "method": method, "batches": []}

    for offset, batch in enumerate(batches):
        batch_id = str(next_no + offset)
        role_map = device.roles(adb)
        guard.require_batch(batch, cat, device.role_holders(role_map), method=method,
                            states=device.package_states(adb))
        entry = {"batch": batch_id, "items": [], "status": "done"}
        stop, blocked = None, False
        app.say("Batch %s:" % batch_id)
        try:
            for it in batch:
                if it["kind"] == "package":
                    status, detail = ops.change_package(ctx, batch_id, it["target"], method)
                elif it["kind"] == "setting":
                    status, detail = ops.change_setting(ctx, batch_id, it["namespace"], it["key"], it["value"])
                else:
                    status, detail = dns.set_private_dns(ctx, batch_id, it["target"])
                entry["items"].append({"id": it["id"], "status": status, "detail": detail})
                app.say("  %-45s %s (%s)" % (it["id"], status, detail))
                if status in ("blocked", "failed"):
                    stop = "%s: %s" % (it["id"], detail)
                    blocked = status == "blocked"
                    break
        except (AdReceiptsError, KeyboardInterrupt, OSError) as exc:
            interrupted(app, ctx, batch_id, exc)
        if not stop:
            try:
                problems = ops.health_check(adb, baseline, app.sleep)
            except (AdReceiptsError, KeyboardInterrupt, OSError) as exc:
                interrupted(app, ctx, batch_id, exc)
            if problems:
                stop = "health check failed: " + "; ".join(problems)
        if stop:
            failures = ops.undo_batch(ctx, batch_id)
            entry["status"] = "undone"
            entry["stop"] = stop
            entry["undo_failures"] = failures
            summary["batches"].append(entry)
            write_json(run_dir / "apply.json", summary)
            if blocked:
                plan["approved"] = None
                plan.setdefault("blocked", []).append({"item": stop, "time": now_iso()})
                write_json(run_dir / "plan.json", plan)
            msg = "Stopped at batch %s. %s. The batch was undone%s." % (
                batch_id, stop, (" except: " + "; ".join(failures)) if failures else "")
            hint = "Earlier batches stay applied. Undo everything with: python adreceipts.py restore --all"
            if blocked:
                hint = ("The phone blocks this method. AdReceipts never switches method on its own. "
                        "A new plan approval is needed; the advanced option is apply --method uninstall "
                        "--i-understand-uninstall. " + hint)
            raise RunStopped(msg, hint=hint)
        journal.write_scripts()
        summary["batches"].append(entry)
        app.say("  read-back and health checks passed")

    plan["applied"] = now_iso()
    write_json(run_dir / "plan.json", plan)
    write_json(run_dir / "apply.json", summary)
    app.say("", "All batches applied. Every change is in journal.jsonl and can be undone.",
            "Next: python adreceipts.py verify")
    return 0
