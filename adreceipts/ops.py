"""Single changes with read-back, their reversal, and health checks."""

from __future__ import annotations

import re

from . import device
from .errors import AdReceiptsError
from .guard import SETTING_VALUE_RE
from .journal import reverse_commands

BLOCKED = re.compile(
    r"SecurityException|Shell cannot change component state|Cannot disable|not allowed|"
    r"Cannot change|is not changeable|DELETE_FAILED_USER_RESTRICTED|DELETE_FAILED_INTERNAL_ERROR",
    re.I,
)


class Context:
    """What a change needs: adb with write access, the journal, a sleep function."""

    def __init__(self, adb, journal, sleep, settle=1.0, attempts=3):
        self.adb = adb
        self.journal = journal
        self.sleep = sleep
        self.settle = settle
        self.attempts = attempts


def _wait_for(ctx, check):
    for _ in range(max(1, ctx.attempts)):
        ctx.sleep(ctx.settle)
        value = check()
        if value[0]:
            return value
    return value


def change_package(ctx, batch, name, method="disable"):
    """Disable (or uninstall for user 0) one package. Returns (status, detail).

    status: done | skipped | blocked | failed
    Never switches method: a blocked disable is reported, not retried another way.
    """
    before = device.package_state(ctx.adb, name)
    if before["state"] != "enabled":
        return "skipped", "already %s before AdReceipts" % before["state"]
    op = "disable" if method == "disable" else "uninstall"
    cid = ctx.journal.intent(batch, op, name, before)
    if op == "disable":
        res = ctx.adb.shell("pm", "disable-user", "--user", "0", name)
        expected = "disabled"
    else:
        res = ctx.adb.shell("pm", "uninstall", "-k", "--user", "0", name)
        expected = "removed"
    output = (res.text + "\n" + res.err_text).strip()
    if BLOCKED.search(output):
        after = device.package_state(ctx.adb, name)
        ctx.journal.mark(cid, "blocked", after=after, note=output[:300])
        return "blocked", "the phone refused this change (manufacturer block): %s" % output.splitlines()[0][:200]

    ok, after = _wait_for(ctx, lambda: _state_is(ctx.adb, name, expected))
    if ok:
        ctx.journal.mark(cid, "done", after=after)
        return "done", "%s -> %s" % (before["state"], after["state"])
    ctx.journal.mark(cid, "failed", after=after, note=output[:300])
    return "failed", "read-back shows %s instead of %s" % (after["state"], expected)


def _state_is(adb, name, expected):
    st = device.package_state(adb, name)
    return st["state"] == expected, st


def change_setting(ctx, batch, namespace, key, value):
    before = device.setting(ctx.adb, namespace, key)
    if before == value:
        return "skipped", "already %s" % value
    if before is not None and not SETTING_VALUE_RE.match(before):
        return "failed", "the current value could not be put back safely, so it was not changed"
    cid = ctx.journal.intent(batch, "setting", "%s/%s" % (namespace, key), {"value": before},
                             namespace=namespace, key=key, value=value)
    ctx.adb.shell("settings", "put", namespace, key, value)
    ok, after = _wait_for(ctx, lambda: _setting_is(ctx.adb, namespace, key, value))
    if ok:
        ctx.journal.mark(cid, "done", after={"value": after})
        return "done", "%s -> %s" % (before, after)
    ctx.journal.mark(cid, "failed", after={"value": after})
    return "failed", "read-back shows %r instead of %r" % (after, value)


def _setting_is(adb, namespace, key, value):
    v = device.setting(adb, namespace, key)
    return v == value, v


def current_matches_before(adb, change):
    op, before = change["op"], change.get("before") or {}
    if op in ("disable", "uninstall"):
        st = device.package_state(adb, change["target"])
        return st["state"] == before.get("state"), st
    if op == "setting":
        v = device.setting(adb, change["namespace"], change["key"])
        return v == before.get("value"), {"value": v}
    if op == "dns":
        mode = device.setting(adb, "global", "private_dns_mode")
        spec = device.setting(adb, "global", "private_dns_specifier")
        want_spec = before.get("specifier") or None
        return (mode == before.get("mode") and spec == want_spec), {"mode": mode, "specifier": spec}
    return False, None


def reverse(ctx, change, phase):
    """Put one change back to its 'before' state. Returns (ok, detail)."""
    ok, now = current_matches_before(ctx.adb, change)
    if ok:
        ctx.journal.mark(change["id"], phase, after=now, note="already in its original state")
        return True, "already in its original state"
    try:
        commands = reverse_commands(change)
    except AdReceiptsError as exc:
        return False, exc.message
    for args in commands:
        ctx.adb.run(args)
    ok, now = _wait_for(ctx, lambda: current_matches_before(ctx.adb, change))
    if ok:
        ctx.journal.mark(change["id"], phase, after=now)
        return True, "restored"
    return False, "read-back after undo shows %r" % (now,)


def undo_batch(ctx, batch):
    """Reverse every open change of one batch, newest first. Returns a list of failures."""
    failures = []
    for change in ctx.journal.open_changes(batch=batch):
        ok, detail = reverse(ctx, change, "undone")
        if not ok:
            failures.append("%s: %s" % (change["target"], detail))
    ctx.journal.write_scripts()
    return failures


# ---- health checks -------------------------------------------------------

def health_baseline(adb, role_map):
    home = (role_map.get("home") or [None])[0]
    return {
        "systemui_pid": device.pid(adb, "com.android.systemui"),
        "home": home,
        "dialer": list(role_map.get("dialer") or []),
        "sms": list(role_map.get("sms") or []),
    }


def health_check(adb, baseline, sleep, retries=3):
    """Return a list of problems (empty when healthy)."""
    problems = []
    reachable = False
    for _ in range(retries):
        res = adb.run(["get-state"])
        if res.rc == 0 and res.text.strip() == "device":
            reachable = True
            break
        sleep(2)
    if not reachable:
        return ["the phone is not reachable over adb any more"]
    if adb.shell_text("getprop", "sys.boot_completed").strip() != "1":
        problems.append("the phone is not fully started (boot not completed)")
    if baseline.get("home") and not device.pid(adb, baseline["home"]):
        problems.append("the home screen app (%s) is not running" % baseline["home"])
    ui = device.pid(adb, "com.android.systemui")
    if not ui:
        problems.append("System UI is not running")
    elif baseline.get("systemui_pid") and ui != baseline["systemui_pid"]:
        problems.append("System UI restarted (it may have crashed)")
    states = device.package_states(adb)
    for label in ("dialer", "sms"):
        for name in baseline.get(label, []):
            if states.get(name, {}).get("state") != "enabled":
                problems.append("the %s app %s is not enabled any more" % ("phone" if label == "dialer" else "SMS", name))
    return problems
