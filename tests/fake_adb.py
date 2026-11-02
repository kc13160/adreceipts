#!/usr/bin/env python3
"""A fake adb that simulates one Android phone and records every command.

Two ways to use it:
  - in-process: FakeDevice() is a callable runner for adreceipts.cli.main(runner=...);
  - as a program: python tests/fake_adb.py <adb args>, with the phone state in
    the JSON file named by FAKE_ADB_STATE and the command log in FAKE_ADB_LOG.
    AdReceipts runs a --adb path ending in .py with the current Python.

Nothing here talks to a real phone. Everything it outputs is SIMULATED.
"""

from __future__ import annotations

import copy
import json
import os
import struct
import sys
import zlib
from pathlib import Path

HOME = "com.miui.home"


def default_state():
    pk = {}

    def add(name, system=True, state="enabled"):
        pk[name] = {"system": system, "state": state}

    for n in ("android", "com.android.systemui", "com.android.settings", "com.android.phone", "com.android.shell",
              "com.android.providers.downloads", "com.android.providers.downloads.ui", HOME,
              "com.miui.securitycenter", "com.miui.msa.global", "com.miui.analytics", "com.miui.daemon",
              "com.miui.android.fashiongallery", "com.mi.globalminusscreen", "com.android.thememanager",
              "com.miui.player", "com.miui.videoplayer", "com.mi.globalbrowser", "com.miui.hybrid",
              "com.android.egg", "com.android.printservice.recommendation", "com.google.android.dialer",
              "com.google.android.apps.messaging", "com.google.android.webview", "com.google.android.inputmethod.latin",
              "com.google.android.googlequicksearchbox", "com.xiaomi.finddevice", "com.google.android.gms",
              "com.google.android.adservices.api", "com.android.vending"):
        add(n)
    add("com.android.dreams.basic", state="disabled")
    add("com.example.mybank", system=False)
    add("com.example.adsdk.analytics", system=False)
    return {
        "serial": "SIMULATED0001",
        "devices": ["device"],
        "props": {
            "ro.product.brand": "Xiaomi",
            "ro.product.manufacturer": "Xiaomi",
            "ro.product.model": "SIMULATED-PHONE",
            "ro.product.device": "simulated",
            "ro.build.version.release": "16",
            "ro.build.version.sdk": "36",
            "ro.build.display.id": "SIMULATED.BUILD",
            "ro.build.fingerprint": "Xiaomi/simulated/simulated:16/SIM1/OS3.0.301.0.SIMULATED:user/release-keys",
            "ro.mi.os.version.name": "OS3.0",
            "ro.mi.os.version.incremental": "OS3.0.301.0.SIMULATED",
            "ro.miui.region": "GLOBAL",
            "ro.serialno": "SIMULATED0001",
            "ro.adreceipts.simulated": "1",
            "sys.boot_completed": "1",
        },
        "packages": pk,
        "settings": {
            "global": {"private_dns_mode": "off"},
            "secure": {
                "default_input_method": "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME",
                "enabled_input_methods": "com.google.android.inputmethod.latin/com.android.inputmethod.latin.LatinIME",
            },
            "system": {},
        },
        "roles": {
            "android.app.role.HOME": [HOME],
            "android.app.role.DIALER": ["com.google.android.dialer"],
            "android.app.role.SMS": ["com.google.android.apps.messaging"],
            "android.app.role.BROWSER": ["com.mi.globalbrowser"],
            "android.app.role.ASSISTANT": ["com.google.android.googlequicksearchbox"],
        },
        "webview": "com.google.android.webview",
        "device_admins": ["com.xiaomi.finddevice"],
        "work_profile": False,
        "device_owner": False,
        "profile_owner": False,
        "foreground": HOME,
        "pids": {"com.android.systemui": 1234, HOME: 2345},
        # Screen text per app. An entry in "ads_need" shows ad words only while that package is enabled.
        "ui_text": {
            "com.miui.securitycenter": ["Security", "Scan", "Ad", "Cleaner"],
            "com.android.thememanager": ["Themes", "Sponsored", "Wallpapers"],
        },
        "ads_need": {"com.miui.securitycenter": "com.miui.msa.global", "com.android.thememanager": "com.miui.msa.global"},
        "screens_dir": None,
        "faults": {
            "blocked_disable": [],
            "readback_ignored": [],
            "enable_ignored": [],
            "crash_systemui_on": [],
            "dns_fails": False,
            "foreground_stuck": None,
            "unreachable_after_write": False,
        },
    }


def tiny_png(width=36, height=64, rgb=(200, 200, 200)):
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


WRITE_PREFIXES = (
    ("shell", "pm", "disable-user"), ("shell", "pm", "disable"), ("shell", "pm", "enable"),
    ("shell", "pm", "uninstall"), ("shell", "pm", "install"), ("shell", "pm", "clear"),
    ("shell", "pm", "hide"), ("shell", "pm", "suspend"), ("shell", "pm", "default-state"),
    ("shell", "cmd", "package", "install-existing"), ("shell", "settings", "put"), ("shell", "settings", "delete"),
    ("shell", "am", "start"), ("shell", "input"), ("exec-out", "screencap"), ("exec-out", "uiautomator"),
    ("shell", "screencap"), ("shell", "uiautomator"), ("install",), ("uninstall",), ("push",), ("reboot",),
    ("root",), ("remount",), ("shell", "svc"), ("shell", "cmd", "role", "add-role-holder"),
)


def is_write(args):
    """Independent of AdReceipts' own classifier: anything that changes the phone or its screen."""
    return any(tuple(args[: len(p)]) == p for p in WRITE_PREFIXES)


class FakeDevice:
    def __init__(self, state=None):
        self.state = state if state is not None else default_state()
        self.log = []
        self.writes_seen = 0

    # -- helpers ---------------------------------------------------------
    def _pkg(self, name):
        return self.state["packages"].get(name)

    def writes(self):
        return [a for a in self.log if is_write(a)]

    def __call__(self, args, timeout=30):
        args = list(args)
        self.log.append(args)
        if is_write(args):
            self.writes_seen += 1
        rc, out, err = self.handle(args)
        if isinstance(out, str):
            out = out.encode("utf-8")
        if isinstance(err, str):
            err = err.encode("utf-8")
        return rc, out, err

    def handle(self, a):
        s = self.state
        if a == ["version"]:
            return 0, "Android Debug Bridge version 1.0.41\nVersion SIMULATED (fake adb)\n", ""
        if a == ["devices"]:
            lines = ["List of devices attached"]
            for n, st in enumerate(s["devices"]):
                lines.append("SIMULATED%04d\t%s" % (n + 1, st))
            return 0, "\n".join(lines) + "\n\n", ""
        if a == ["get-serialno"]:
            return 0, s["serial"] + "\n", ""
        if a == ["get-state"]:
            if s["faults"].get("unreachable_after_write") and self.writes_seen:
                return 1, "", "error: no devices/emulators found\n"
            return 0, "device\n", ""
        if a[:1] == ["shell"]:
            return self.shell(a[1:])
        if a[:1] == ["exec-out"]:
            return self.exec_out(a[1:])
        return 1, "", "fake adb: unsupported command %r\n" % (a,)

    def exec_out(self, a):
        s = self.state
        if a == ["uiautomator", "dump", "/dev/tty"]:
            fg = s["foreground"]
            texts = list(s["ui_text"].get(fg, ["Home"]))
            need = s["ads_need"].get(fg)
            if need and (self._pkg(need) or {}).get("state") != "enabled":
                texts = [t for t in texts if t not in ("Ad", "Ads", "Sponsored")]
            nodes = "".join('<node index="%d" text="%s" content-desc="" package="%s"/>' % (i, t, fg) for i, t in enumerate(texts))
            return 0, '<?xml version="1.0" encoding="UTF-8"?><hierarchy rotation="0">%s</hierarchy>UI hierchary dumped to: /dev/tty' % nodes, ""
        if a == ["screencap", "-p"]:
            fg = s["foreground"]
            d = s.get("screens_dir")
            if d:
                need = s["ads_need"].get(fg)
                variant = "ads" if (need and (self._pkg(need) or {}).get("state") == "enabled") else "clean"
                for name in ("%s-%s.png" % (fg, variant), "%s.png" % fg):
                    p = Path(d) / name
                    if p.exists():
                        return 0, p.read_bytes(), ""
            return 0, tiny_png(), ""
        return 1, "", "fake adb: unsupported exec-out %r\n" % (a,)

    def _list(self, flags):
        out = []
        for name, p in sorted(self.state["packages"].items()):
            if "-s" in flags and not p["system"]:
                continue
            if "-u" not in flags and p["state"] == "removed":
                continue
            if "-d" in flags and p["state"] != "disabled":
                continue
            if "-e" in flags and p["state"] != "enabled":
                continue
            out.append("package:" + name)
        return "\n".join(out) + "\n"

    def shell(self, a):
        s = self.state
        f = s["faults"]
        if a == ["getprop"]:
            return 0, "".join("[%s]: [%s]\n" % kv for kv in sorted(s["props"].items())), ""
        if a[:1] == ["getprop"] and len(a) == 2:
            return 0, s["props"].get(a[1], "") + "\n", ""
        if a[:3] == ["pm", "list", "packages"]:
            return 0, self._list(a[3:]), ""
        if a == ["pm", "list", "users"]:
            text = "Users:\n\tUserInfo{0:Owner:c13} running\n"
            if s.get("work_profile"):
                text += "\tUserInfo{10:Work profile:1030} running\n"
            return 0, text, ""
        if a[:2] == ["pm", "disable-user"] and a[2:4] == ["--user", "0"] and len(a) == 5:
            name = a[4]
            p = self._pkg(name)
            if not p:
                return 1, "", "Error: Unknown package: %s\n" % name
            if name in f["blocked_disable"]:
                return 255, "Exception occurred while executing 'disable-user':\njava.lang.SecurityException: Shell cannot change component state for %s to 3\n" % name, ""
            if name not in f["readback_ignored"]:
                p["state"] = "disabled"
                if name in s["pids"] and name != "com.android.systemui":
                    s["pids"].pop(name)
            if name in f["crash_systemui_on"]:
                s["pids"]["com.android.systemui"] = s["pids"].get("com.android.systemui", 1) + 100
            return 0, "Package %s new state: disabled-user\n" % name, ""
        if a[:2] == ["pm", "enable"] and a[2:4] == ["--user", "0"] and len(a) == 5:
            name = a[4]
            p = self._pkg(name)
            if not p:
                return 1, "", "Error: Unknown package: %s\n" % name
            if name not in f["enable_ignored"]:
                p["state"] = "enabled" if p["state"] != "removed" else "removed"
            return 0, "Package %s new state: enabled\n" % name, ""
        if a[:3] == ["pm", "uninstall", "-k"] and a[3:5] == ["--user", "0"] and len(a) == 6:
            name = a[5]
            p = self._pkg(name)
            if not p:
                return 1, "Failure [not installed for 0]\n", ""
            if p["system"]:
                p["state"] = "removed"
            else:
                del s["packages"][name]
            return 0, "Success\n", ""
        if a[:3] == ["cmd", "package", "install-existing"] and a[3:5] == ["--user", "0"] and len(a) == 6:
            p = self._pkg(a[5])
            if not p:
                return 1, "Package %s doesn't exist\n" % a[5], ""
            if p["state"] == "removed":
                p["state"] = "enabled"
            return 0, "Package %s installed for user: 0\n" % a[5], ""
        if a[:3] == ["cmd", "package", "resolve-activity"]:
            if "android.intent.category.HOME" in a:
                return 0, "priority=0 preferredOrder=0 match=0x108000\n%s/.launcher.Launcher\n" % s["roles"]["android.app.role.HOME"][0], ""
            name = a[-1]
            if self._pkg(name) and self._pkg(name)["state"] == "enabled":
                return 0, "priority=0 preferredOrder=0 match=0x108000\n%s/.MainActivity\n" % name, ""
            return 0, "No activity found\n", ""
        if a[:3] == ["cmd", "role", "get-role-holders"] and len(a) == 4:
            return 0, "".join(n + "\n" for n in s["roles"].get(a[3], [])), ""
        if a[:2] == ["settings", "get"] and len(a) == 4:
            v = s["settings"].get(a[2], {}).get(a[3])
            return 0, ("null" if v is None else v) + "\n", ""
        if a[:2] == ["settings", "put"] and len(a) == 5:
            s["settings"].setdefault(a[2], {})[a[3]] = a[4]
            return 0, "", ""
        if a[:2] == ["settings", "delete"] and len(a) == 4:
            s["settings"].get(a[2], {}).pop(a[3], None)
            return 0, "Deleted 1 rows\n", ""
        if a == ["dumpsys", "device_policy"]:
            text = "Current Device Policy Manager state:\n"
            if s.get("device_owner"):
                text += "  Device Owner: \n    admin=ComponentInfo{com.example.mdm/com.example.mdm.Admin}\n"
            if s.get("profile_owner"):
                text += "  Profile Owner (User 10): \n    admin=ComponentInfo{com.example.mdm/com.example.mdm.Admin}\n"
            text += "  Enabled Device Admins (User 0, provisioning state: 3):\n"
            for adm in s["device_admins"]:
                text += "    %s/.Admin:\n      uid=10100\n" % adm
                text += "      ComponentInfo{%s/%s.Admin}\n" % (adm, adm)
            return 0, text, ""
        if a == ["dumpsys", "webviewupdate"]:
            return 0, "Current WebView package (name, version): (%s, 120.0.0.1)\n" % s["webview"], ""
        if a == ["dumpsys", "activity", "activities"]:
            return 0, "  mResumedActivity: ActivityRecord{1a2b u0 %s/.MainActivity t42}\n" % s["foreground"], ""
        if a == ["dumpsys", "window", "windows"]:
            focus = s.get("focus_override") or s["foreground"]
            return 0, "  mCurrentFocus=Window{3c4d u0 %s/.MainActivity}\n" % focus, ""
        if a[:1] == ["pidof"] and len(a) == 2:
            name = a[1]
            p = self._pkg(name)
            pid = s["pids"].get(name)
            if pid and p and p["state"] == "enabled":
                return 0, "%d\n" % pid, ""
            return 1, "", ""
        if a[:3] == ["ping", "-c", "1"]:
            host = a[-1]
            if f.get("dns_fails") and s["settings"]["global"].get("private_dns_mode") == "hostname":
                return 2, "", "ping: unknown host %s\n" % host
            return 0, "PING %s (142.250.0.1) 56(84) bytes of data.\n64 bytes from 142.250.0.1: icmp_seq=1 ttl=117 time=12 ms\n" % host, ""
        if a[:3] == ["am", "start", "-n"] and len(a) == 4:
            pkg = a[3].split("/")[0]
            if not f.get("foreground_stuck"):
                s["foreground"] = pkg
            else:
                s["foreground"] = f["foreground_stuck"]
            return 0, "Starting: Intent { cmp=%s }\n" % a[3], ""
        if a == ["input", "keyevent", "KEYCODE_HOME"]:
            s["foreground"] = s["roles"]["android.app.role.HOME"][0]
            return 0, "", ""
        return 127, "", "/system/bin/sh: fake: unsupported %r\n" % (a,)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    state_path = os.environ.get("FAKE_ADB_STATE")
    log_path = os.environ.get("FAKE_ADB_LOG")
    state = None
    if state_path and Path(state_path).exists():
        state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    dev = FakeDevice(copy.deepcopy(state) if state else None)
    if state_path:
        # Writes seen in earlier calls of the same session count for "unreachable_after_write".
        dev.writes_seen = dev.state.get("_writes_seen", 0)
    rc, out, err = dev(argv)
    if state_path:
        dev.state["_writes_seen"] = dev.writes_seen
        Path(state_path).write_text(json.dumps(dev.state, indent=1), encoding="utf-8")
    if log_path:
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(argv) + "\n")
    sys.stdout.buffer.write(out)
    sys.stderr.buffer.write(err)
    return rc


if __name__ == "__main__":
    sys.exit(main())
