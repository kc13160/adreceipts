"""Reading the phone's state with read-only adb commands."""

from __future__ import annotations

import re

from .errors import AdbError, SafetyStop
from .store import hash_id

# Only these properties are kept. Serial numbers and other IDs are never stored.
KEPT_PROPS = (
    "ro.product.brand",
    "ro.product.manufacturer",
    "ro.product.model",
    "ro.product.device",
    "ro.build.version.release",
    "ro.build.version.sdk",
    "ro.build.display.id",
    "ro.mi.os.version.name",
    "ro.mi.os.version.incremental",
    "ro.miui.ui.version.name",
    "ro.miui.region",
    "ro.adreceipts.simulated",
)

ROLES = {
    "home": "android.app.role.HOME",
    "dialer": "android.app.role.DIALER",
    "sms": "android.app.role.SMS",
    "browser": "android.app.role.BROWSER",
    "assistant": "android.app.role.ASSISTANT",
}

PKG_LINE = re.compile(r"^package:([A-Za-z][A-Za-z0-9_.]*)\s*$")
PKG_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")
PROP_LINE = re.compile(r"^\[([^\]]+)\]: \[(.*)\]$")


def _packages(text):
    out = set()
    for line in text.splitlines():
        m = PKG_LINE.match(line.strip())
        if m:
            out.add(m.group(1))
    return out


def list_devices(adb):
    """Return a list of (state) for each connected device. Serials are not kept."""
    res = adb.run(["devices"])
    if res.rc != 0:
        raise AdbError("adb could not list devices.", hint=res.err_text.strip() or None)
    states = []
    for line in res.text.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            states.append(parts[1])
    return states


def require_one_device(adb):
    states = list_devices(adb)
    if not states:
        raise AdbError(
            "No phone is connected.",
            hint="Connect the phone with a USB cable and turn on USB debugging.",
        )
    if len(states) > 1:
        raise SafetyStop(
            "%d devices are connected. AdReceipts works with exactly one." % len(states),
            hint="Unplug the other phones or emulators.",
        )
    state = states[0]
    if state == "unauthorized":
        raise AdbError(
            "The phone has not authorized this computer.",
            hint="Unlock the phone and accept the 'Allow USB debugging?' prompt.",
        )
    if state != "device":
        raise AdbError(
            "The phone is connected but not ready (state: %s)." % state,
            hint="Unplug and reconnect the cable, then unlock the phone.",
        )


def props(adb):
    text = adb.shell_text("getprop")
    out = {}
    for line in text.splitlines():
        m = PROP_LINE.match(line.strip())
        if m and m.group(1) in KEPT_PROPS:
            out[m.group(1)] = m.group(2)
    return out


def fingerprint(adb, home):
    """Hashed identity of this phone and its system build. Raw values are not stored."""
    serial = adb.run(["get-serialno"]).text.strip()
    build = adb.shell_text("getprop", "ro.build.fingerprint").strip()
    return {"id_hash": hash_id(home, serial), "build_hash": hash_id(home, build)}


def describe(p):
    brand = p.get("ro.product.brand") or p.get("ro.product.manufacturer") or "unknown"
    system = p.get("ro.mi.os.version.incremental") or p.get("ro.mi.os.version.name") or p.get("ro.build.display.id") or ""
    return {
        "brand": brand,
        "model": p.get("ro.product.model", ""),
        "android": p.get("ro.build.version.release", ""),
        "sdk": p.get("ro.build.version.sdk", ""),
        "system": system,
        "simulated": p.get("ro.adreceipts.simulated") == "1",
    }


def identity(adb, home):
    p = props(adb)
    d = describe(p)
    d.update(fingerprint(adb, home))
    return p, d


def package_states(adb):
    """{name: {"state": enabled|disabled|removed, "system": bool}} for user 0."""
    installed = _packages(adb.shell_text("pm", "list", "packages", "--user", "0"))
    disabled = _packages(adb.shell_text("pm", "list", "packages", "-d", "--user", "0"))
    every = _packages(adb.shell_text("pm", "list", "packages", "-u", "--user", "0"))
    system = _packages(adb.shell_text("pm", "list", "packages", "-s", "-u", "--user", "0"))
    out = {}
    for name in every | installed:
        if name not in installed:
            state = "removed"
        elif name in disabled:
            state = "disabled"
        else:
            state = "enabled"
        out[name] = {"state": state, "system": name in system}
    return out


def package_state(adb, name):
    return package_states(adb).get(name, {"state": "absent", "system": False})


def setting(adb, namespace, key):
    res = adb.shell("settings", "get", namespace, key)
    value = res.text.strip()
    if res.rc != 0:
        return None
    return None if value in ("", "null") else value


def users_and_policy(adb):
    """Detect work profiles and managed phones. Returns a list of reasons to stop."""
    reasons = []
    users = adb.shell_text("pm", "list", "users")
    for m in re.finditer(r"UserInfo\{(\d+):([^:}]*):([0-9a-fA-F]+)\}", users):
        flags = int(m.group(3), 16)
        if flags & 0x20:
            reasons.append("a work profile (user %s)" % m.group(1))
    policy = adb.shell_text("dumpsys", "device_policy")
    if re.search(r"(?m)^\s*Device Owner:", policy) or re.search(r"(?m)^\s*Device Owner\b.*admin=", policy):
        reasons.append("a device owner (the phone is managed by an organization)")
    if re.search(r"(?m)^\s*Profile Owner", policy):
        reasons.append("a profile owner (work or school management)")
    return reasons


def require_unmanaged(adb):
    reasons = users_and_policy(adb)
    if reasons:
        raise SafetyStop(
            "This phone has %s. AdReceipts does not touch managed phones or work profiles." % ", ".join(reasons),
            hint="Nothing was changed. Ask the organization that manages the phone.",
        )


def _role_holders(adb, role):
    res = adb.shell("cmd", "role", "get-role-holders", role)
    if res.rc != 0:
        return []
    return [l.strip() for l in res.text.splitlines() if PKG_NAME.match(l.strip())]


def _component_pkgs(value):
    out = []
    for part in (value or "").split(":"):
        pkg = part.split("/")[0].strip()
        if PKG_NAME.match(pkg):
            out.append(pkg)
    return out


def roles(adb):
    """Packages that must stay untouched because they hold a role right now."""
    out = {}
    for label, role in ROLES.items():
        out[label] = _role_holders(adb, role)
    if not out["home"]:
        res = adb.shell("cmd", "package", "resolve-activity", "--brief", "-a", "android.intent.action.MAIN",
                        "-c", "android.intent.category.HOME")
        lines = [l.strip() for l in res.text.splitlines() if "/" in l]
        out["home"] = _component_pkgs(lines[-1]) if lines else []
    out["keyboard"] = _component_pkgs(setting(adb, "secure", "default_input_method"))
    out["keyboards_enabled"] = _component_pkgs(setting(adb, "secure", "enabled_input_methods"))
    out["accessibility"] = _component_pkgs(setting(adb, "secure", "enabled_accessibility_services"))
    web = adb.shell_text("dumpsys", "webviewupdate")
    m = re.search(r"Current WebView package \(name, version\): \(([A-Za-z0-9_.]+),", web)
    out["webview"] = [m.group(1)] if m else []
    policy = adb.shell_text("dumpsys", "device_policy")
    admins = set()
    for m in re.finditer(r"ComponentInfo\{([A-Za-z0-9_.]+)/", policy):
        admins.add(m.group(1))
    out["device_admin"] = sorted(admins)
    return out


def role_holders(role_map):
    held = set()
    for names in role_map.values():
        held.update(names)
    return held


def foreground(adb):
    text = adb.shell_text("dumpsys", "activity", "activities")
    m = re.search(r"(?:mResumedActivity|topResumedActivity|ResumedActivity)[:=]\s*ActivityRecord\{\S+ \S+ ([A-Za-z0-9_.]+)/", text)
    if m:
        return m.group(1)
    text = adb.shell_text("dumpsys", "window", "windows")
    m = re.search(r"mCurrentFocus=Window\{\S+ \S+ ([A-Za-z0-9_.]+)/", text)
    return m.group(1) if m else None


def pid(adb, package):
    res = adb.shell("pidof", package)
    value = res.text.strip()
    return value if res.rc == 0 and value else None
