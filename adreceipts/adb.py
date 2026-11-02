"""Talking to adb safely.

Every call is an argument list. Nothing is ever passed through a local shell.
`adb shell` joins its arguments into one string on the phone, so every argument
is checked against a strict pattern before it is sent.

Each command opens adb with the permissions it needs:
  - "read":   reads state only (getprop, pm list, settings get, dumpsys, ...)
  - "screen": opens a catalog surface, dumps UI text, takes a screenshot
  - "write":  changes the phone (disable, enable, settings put, ...)
A read-only command physically cannot send a write: the call is refused here.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass

from .errors import AdbError, SafetyStop

SAFE_ARG = re.compile(r"^[A-Za-z0-9_.:/@=+,-]{1,300}$")

# Commands that only read. Matched on the leading words of an `adb shell` call.
_READ_SHELL_PREFIXES = (
    ("getprop",),
    ("pm", "list", "packages"),
    ("pm", "list", "users"),
    ("pm", "path"),
    ("settings", "get"),
    ("dumpsys", "device_policy"),
    ("dumpsys", "webviewupdate"),
    ("dumpsys", "activity", "activities"),
    ("dumpsys", "window", "windows"),
    ("cmd", "role", "get-role-holders"),
    ("cmd", "package", "resolve-activity"),
    ("pidof",),
    ("ping", "-c", "1"),
)
_READ_TOP = {"version", "devices", "get-state", "get-serialno"}

_SCREEN_SHELL_PREFIXES = (
    ("am", "start", "-n"),
    ("input", "keyevent", "KEYCODE_HOME"),
)
_SCREEN_EXEC_OUT = (
    ("uiautomator", "dump", "/dev/tty"),
    ("screencap", "-p"),
)


def _starts_with(args, prefix):
    return len(args) >= len(prefix) and tuple(args[: len(prefix)]) == prefix


def classify(args):
    """Return "read", "screen" or "write" for an adb argument list."""
    if not args:
        return "write"
    head = args[0]
    if head in _READ_TOP:
        return "read"
    if head == "shell":
        rest = args[1:]
        if any(_starts_with(rest, p) for p in _READ_SHELL_PREFIXES):
            return "read"
        if any(_starts_with(rest, p) for p in _SCREEN_SHELL_PREFIXES):
            return "screen"
        return "write"
    if head == "exec-out":
        rest = args[1:]
        if any(_starts_with(rest, p) for p in _SCREEN_EXEC_OUT):
            return "screen"
        return "write"
    return "write"


@dataclass
class Result:
    rc: int
    out: bytes
    err: bytes

    @property
    def text(self):
        return self.out.decode("utf-8", "replace")

    @property
    def err_text(self):
        return self.err.decode("utf-8", "replace")


class SubprocessRunner:
    """Runs the real adb (or a Python fake adb used for tests and simulation)."""

    def __init__(self, adb_path):
        self.adb_path = adb_path
        if adb_path.lower().endswith(".py"):
            self.prefix = [sys.executable, adb_path]
        else:
            self.prefix = [adb_path]

    def __call__(self, args, timeout):
        try:
            proc = subprocess.run(
                self.prefix + list(args),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                timeout=timeout,
                shell=False,
            )
        except FileNotFoundError:
            raise AdbError(
                "adb was not found at %s." % self.adb_path,
                hint="Install Android platform-tools, or pass --adb PATH.",
            )
        except subprocess.TimeoutExpired:
            raise AdbError(
                "adb did not answer within %s seconds (%s)." % (timeout, " ".join(args[:3])),
                hint="Unplug and reconnect the phone, then try again.",
            )
        return proc.returncode, proc.stdout, proc.stderr


def find_adb(cli_value=None, environ=None):
    """--adb PATH, then ADRECEIPTS_ADB, then adb on the PATH."""
    environ = os.environ if environ is None else environ
    for candidate in (cli_value, environ.get("ADRECEIPTS_ADB")):
        if candidate:
            if not os.path.isfile(candidate):
                raise AdbError(
                    "adb was not found at %s." % candidate,
                    hint="Check the path given with --adb or ADRECEIPTS_ADB.",
                )
            return candidate
    found = shutil.which("adb")
    if not found:
        raise AdbError(
            "adb was not found.",
            hint="Install Android SDK platform-tools and add it to PATH, or pass --adb PATH.",
        )
    return found


class Adb:
    """adb with a permission level. Every call is checked and recorded."""

    LEVELS = {"read": {"read"}, "screen": {"read", "screen"}, "write": {"read", "screen", "write"}}

    def __init__(self, runner, level="read"):
        if level not in self.LEVELS:
            raise ValueError(level)
        self.runner = runner
        self.level = level
        self.history = []

    def allow(self, level):
        """Return a copy of this adb with another permission level."""
        clone = Adb(self.runner, level)
        clone.history = self.history
        return clone

    def run(self, args, timeout=30, check=False):
        args = [str(a) for a in args]
        for a in args:
            if not SAFE_ARG.match(a):
                raise SafetyStop("Refused to send an unsafe argument to adb: %r" % a)
        kind = classify(args)
        if kind not in self.LEVELS[self.level]:
            raise SafetyStop(
                "Safety stop: this command may only read the phone, "
                "but tried to send %r (%s)." % (" ".join(args), kind)
            )
        self.history.append(args)
        rc, out, err = self.runner(args, timeout)
        result = Result(rc, out or b"", err or b"")
        if check and rc != 0:
            raise AdbError(
                "adb command failed: %s" % " ".join(args[:4]),
                hint=(result.err_text or result.text).strip()[:300] or None,
            )
        return result

    def shell(self, *args, timeout=30, check=False):
        return self.run(["shell"] + list(args), timeout=timeout, check=check)

    def shell_text(self, *args, timeout=30):
        return self.shell(*args, timeout=timeout).text

    def exec_out(self, *args, timeout=30):
        return self.run(["exec-out"] + list(args), timeout=timeout)
