"""Local files: runs, JSON state, the device hash.

Everything stays on this computer, under the data folder (default: ./reports).
The folder is git-ignored.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import secrets
from pathlib import Path

from .errors import AdReceiptsError, SafetyStop

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_ID = re.compile(r"^\d{8}-\d{6}(-\d+)?$")


def data_dir(cli_value=None):
    """Default: <repository>/reports, whatever the current folder is. A .gitignore keeps it out of git."""
    path = cli_value or os.environ.get("ADRECEIPTS_HOME")
    p = Path(path) if path else REPO_ROOT / "reports"
    p.mkdir(parents=True, exist_ok=True)
    ignore = p / ".gitignore"
    if not ignore.exists():
        ignore.write_text("# AdReceipts data: phone state, journals, screenshots. Never commit.\n*\n", encoding="utf-8")
    return p


def _salt(home):
    """A random salt kept on this computer, so device hashes cannot be linked elsewhere."""
    f = Path(home) / ".salt"
    if f.exists():
        value = f.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = secrets.token_hex(16)
    f.write_text(value + "\n", encoding="utf-8")
    return value


def hash_id(home, raw):
    if not raw:
        return "unknown"
    digest = hashlib.sha256((_salt(home) + "|" + raw).encode("utf-8")).hexdigest()
    return digest[:16]


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(path))


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise AdReceiptsError("The file %s is damaged: %s" % (path.name, exc))


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:  # Path.write_text(newline=) needs 3.10
        fh.write(text)


def now_iso(clock=None):
    t = clock() if clock else _dt.datetime.now(_dt.timezone.utc)
    return t.replace(microsecond=0).isoformat()


class Runs:
    """A run is one folder: reports/<run id>/ with scan, backup, drill, plan, journal..."""

    def __init__(self, home, clock=None):
        self.home = Path(home)
        self.clock = clock

    def new(self, device):
        t = self.clock() if self.clock else _dt.datetime.now()
        base = t.strftime("%Y%m%d-%H%M%S")
        run_id, n = base, 1
        while (self.home / run_id).exists():
            n += 1
            run_id = "%s-%d" % (base, n)
        path = self.home / run_id
        path.mkdir(parents=True)
        write_json(path / "run.json", {"run_id": run_id, "created": now_iso(), "device": device})
        return run_id, path

    def all(self):
        if not self.home.exists():
            return []
        found = [p.name for p in self.home.iterdir() if p.is_dir() and RUN_ID.match(p.name) and (p / "run.json").exists()]
        return sorted(found)

    def resolve(self, run_id=None):
        if run_id:
            if not RUN_ID.match(run_id) or not (self.home / run_id / "run.json").exists():
                raise AdReceiptsError("Run %s was not found in %s." % (run_id, self.home))
            return run_id, self.home / run_id
        runs = self.all()
        if not runs:
            raise AdReceiptsError(
                "No run found yet.",
                hint="Start with: python adreceipts.py scan",
            )
        return runs[-1], self.home / runs[-1]


def same_device(saved, current, check_build=True):
    """Device identity: hashed device id, plus the hashed build fingerprint."""
    if not saved or not current:
        return False
    if saved.get("id_hash") != current.get("id_hash"):
        return False
    if check_build and saved.get("build_hash") != current.get("build_hash"):
        return False
    return True


def require_same_device(saved, current, what, check_build=True):
    if not same_device(saved, current, check_build=check_build):
        raise SafetyStop(
            "The %s was made for another phone or another system version." % what,
            hint="Start again on this phone: scan, backup, drill, plan.",
        )
