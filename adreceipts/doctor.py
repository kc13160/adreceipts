"""doctor: check adb, authorization, one device, work profiles. Changes nothing."""

from __future__ import annotations

from . import device
from .errors import AdReceiptsError


def run(app):
    adb = app.adb("read")
    ok = True
    app.say("AdReceipts doctor (read-only: nothing on the phone is changed)", "")

    res = adb.run(["version"])
    first = res.text.strip().splitlines()[0] if res.text.strip() else "unknown"
    app.say("[OK] adb found: %s" % first)

    try:
        device.require_one_device(adb)
        app.say("[OK] exactly one phone is connected and it authorized this computer")
    except AdReceiptsError as exc:
        app.say("[PROBLEM] %s" % exc.message)
        if exc.hint:
            app.say("          %s" % exc.hint)
        return 1

    reasons = device.users_and_policy(adb)
    if reasons:
        app.say("[STOP] this phone has %s. AdReceipts will not continue on managed phones." % ", ".join(reasons))
        return 2
    app.say("[OK] no work profile and no device management found")

    props = device.props(adb)
    dev = device.describe(props)
    app.say("[OK] phone: %s %s, Android %s%s" % (
        dev["brand"], dev["model"], dev["android"] or "?", (", system %s" % dev["system"]) if dev["system"] else ""))
    try:
        sdk = int(dev["sdk"] or 0)
    except ValueError:
        sdk = 0
    if sdk and sdk < 29:
        app.say("[WARN] Android 10 or newer is recommended (role checks need it). Scan still works.")
        ok = False

    if adb.shell_text("getprop", "sys.boot_completed").strip() != "1":
        app.say("[PROBLEM] the phone has not finished starting. Wait and try again.")
        ok = False
    else:
        app.say("[OK] the phone is fully started")

    cat = app.catalog(props)
    detailed = [l for l in cat.labels if not l.startswith("generic/")]
    if detailed:
        app.say("[OK] detailed catalog: %s" % ", ".join(detailed))
    else:
        app.say("[INFO] no detailed catalog for this phone yet: generic checks only. Contributions welcome.")

    role_map = device.roles(adb)
    if not role_map.get("home"):
        app.say("[WARN] could not read the home screen app. Changes will be refused until it can be read.")
        ok = False
    else:
        app.say("[OK] protected right now: home, phone, SMS, browser, assistant, keyboard, WebView, admins, accessibility")
    if dev.get("simulated"):
        app.say("[INFO] SIMULATED phone (fake adb).")
    app.say("", "Next: python adreceipts.py scan   (read-only)")
    return 0 if ok else 1
