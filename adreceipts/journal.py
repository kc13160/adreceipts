"""The journal: every change is logged *before* it is made, then its result.

restore reverses only what this journal recorded. It never touches packages
that were already off before AdReceipts ran.
"""

from __future__ import annotations

import json
from pathlib import Path

from .errors import AdReceiptsError
from .guard import NAMESPACES, SETTING_KEY_RE, SETTING_VALUE_RE, valid_package_name
from .store import now_iso, write_text

OPEN_PHASES = ("intent", "done", "failed", "blocked")
CLOSED_PHASES = ("undone", "restored")


class Journal:
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.path = self.run_dir / "journal.jsonl"
        self.damaged_tail = False

    def _append(self, record):
        record["time"] = now_iso()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
            fh.flush()

    def records(self):
        if not self.path.exists():
            return []
        out = []
        lines = [l for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
        for n, line in enumerate(lines, start=1):
            try:
                out.append(json.loads(line))
            except ValueError:
                if n == len(lines):
                    # A crash while writing can cut the last line. Move it aside so later
                    # records start on a clean line; the intent before it still covers the change.
                    self.damaged_tail = True
                    with open(self.run_dir / "journal-damaged-line.txt", "a", encoding="utf-8") as fh:
                        fh.write(line + "\n")
                    good = "".join(l + "\n" for l in lines[:-1])
                    with open(self.path, "w", encoding="utf-8", newline="\n") as fh:
                        fh.write(good)
                    continue
                raise AdReceiptsError("journal.jsonl line %d is damaged." % n,
                                      hint="Use the standalone restore script in the same folder.")
        return out

    def _next_id(self):
        ids = [r["id"] for r in self.records() if r.get("phase") == "intent"]
        return max(ids) + 1 if ids else 1

    def intent(self, batch, op, target, before, **extra):
        change_id = self._next_id()
        record = {"id": change_id, "phase": "intent", "batch": str(batch), "op": op, "target": target, "before": before}
        record.update(extra)
        self._append(record)
        self.write_scripts()
        return change_id

    def mark(self, change_id, phase, after=None, note=None):
        self._append({"id": change_id, "phase": phase, "after": after, "note": note})

    def changes(self):
        """Merged view: {id: {...intent fields, "phase": latest, "history": [...]}}."""
        out = {}
        for r in self.records():
            cid = r["id"]
            if r["phase"] == "intent":
                out[cid] = dict(r, history=["intent"])
            elif cid in out:
                out[cid]["phase"] = r["phase"]
                out[cid]["history"].append(r["phase"])
                if r.get("after") is not None:
                    out[cid]["after"] = r["after"]
                if r.get("note"):
                    out[cid]["note"] = r["note"]
        return out

    def open_changes(self, batch=None):
        """Changes that may still be in effect, newest first."""
        items = [c for c in self.changes().values() if c["phase"] in OPEN_PHASES]
        if batch is not None:
            items = [c for c in items if c["batch"] == str(batch)]
        return sorted(items, key=lambda c: c["id"], reverse=True)

    def batches(self):
        seen = []
        for c in sorted(self.changes().values(), key=lambda c: c["id"]):
            if c["batch"] not in seen:
                seen.append(c["batch"])
        return seen

    # ---- standalone restore scripts -------------------------------------

    def script_commands(self):
        cmds, skipped = [], []
        for c in self.open_changes():
            try:
                cmds.extend(reverse_commands(c))
            except AdReceiptsError:
                skipped.append(c.get("target"))
        return cmds, skipped

    def write_scripts(self):
        cmds, skipped = self.script_commands()
        header = [
            "AdReceipts standalone restore script.",
            "Reverses only the changes AdReceipts recorded in journal.jsonl, newest first.",
            "Use it if Python is not available. Connect only the phone this was made for.",
        ]
        sh = ["#!/bin/sh"] + ["# " + h for h in header] + ['ADB="${ADB:-adb}"', ""]
        bat = ["@echo off"] + ["rem " + h for h in header] + ['set "ADB_EXE=adb"', 'if defined ADB set "ADB_EXE=%ADB%"', ""]
        if not cmds:
            sh.append('echo "Nothing to restore: no change is recorded yet."')
            bat.append("echo Nothing to restore: no change is recorded yet.")
        for target in skipped:
            sh.append("# Not included (unsafe value in the journal), undo by hand: %s" % _comment(target))
            bat.append("rem Not included (unsafe value in the journal), undo by hand: %s" % _comment(target))
        for args in cmds:
            sh.append('"$ADB" ' + " ".join(args))
            bat.append('"%ADB_EXE%" ' + " ".join(args))
        sh.append('echo "Done. Check the phone, then run: python adreceipts.py recheck"')
        bat.append("echo Done. Check the phone, then run: python adreceipts.py recheck")
        write_text(self.run_dir / "restore-standalone.sh", "\n".join(sh) + "\n")
        write_text(self.run_dir / "restore-standalone.cmd", "\r\n".join(bat) + "\r\n")


def _comment(value):
    return "".join(c for c in str(value) if c.isalnum() or c in "._-/")[:120]


def _safe(value, pattern):
    if not pattern.match(value):
        raise AdReceiptsError("Refused to write an unsafe value into the restore script: %r" % value)
    return value


def reverse_commands(change):
    """adb argument lists that undo one journal change."""
    op, target, before = change["op"], change["target"], change.get("before") or {}
    if op == "disable":
        if not valid_package_name(target):
            raise AdReceiptsError("Bad package name in journal: %r" % target)
        return [["shell", "pm", "enable", "--user", "0", target]]
    if op == "uninstall":
        if not valid_package_name(target):
            raise AdReceiptsError("Bad package name in journal: %r" % target)
        cmds = [["shell", "cmd", "package", "install-existing", "--user", "0", target]]
        if before.get("state") == "enabled":
            cmds.append(["shell", "pm", "enable", "--user", "0", target])
        return cmds
    if op == "setting":
        ns = change.get("namespace")
        if ns not in NAMESPACES:
            raise AdReceiptsError("Bad namespace in journal: %r" % ns)
        key = _safe(change["key"], SETTING_KEY_RE)
        value = before.get("value")
        if value is None:
            return [["shell", "settings", "delete", ns, key]]
        return [["shell", "settings", "put", ns, key, _safe(value, SETTING_VALUE_RE)]]
    if op == "dns":
        mode = before.get("mode")
        spec = before.get("specifier")
        cmds = []
        if spec is None or spec == "":
            cmds.append(["shell", "settings", "delete", "global", "private_dns_specifier"])
        else:
            cmds.append(["shell", "settings", "put", "global", "private_dns_specifier", _safe(spec, SETTING_VALUE_RE)])
        if mode is None:
            cmds.append(["shell", "settings", "delete", "global", "private_dns_mode"])
        else:
            cmds.append(["shell", "settings", "put", "global", "private_dns_mode", _safe(mode, SETTING_VALUE_RE)])
        return cmds
    raise AdReceiptsError("Unknown change in journal: %r" % op)
