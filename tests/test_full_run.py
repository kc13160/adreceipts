"""A full simulated run through the real command line and a real subprocess (fake adb as --adb)."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAKE = ROOT / "tests" / "fake_adb.py"


def run_cli(args, env, cwd):
    proc = subprocess.run([sys.executable, str(ROOT / "adreceipts.py")] + args, cwd=str(cwd), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def test_full_simulated_run(tmp_path):
    state = tmp_path / "phone.json"
    log = tmp_path / "adb-log.jsonl"
    env = dict(os.environ, FAKE_ADB_STATE=str(state), FAKE_ADB_LOG=str(log), ADRECEIPTS_ADB=str(FAKE),
               ADRECEIPTS_HOME=str(tmp_path / "reports"), PYTHONIOENCODING="utf-8")
    sys.path.insert(0, str(ROOT / "tests"))
    from fake_adb import default_state
    initial = default_state()
    state.write_text(json.dumps(initial), encoding="utf-8")

    steps = [
        ["doctor"],
        ["scan"],
        ["backup"],
        ["drill"],
        ["plan"],
        ["plan", "--select", "pkg:com.miui.msa.global", "pkg:com.miui.analytics", "--approve"],
        ["apply"],
        ["apply", "--execute"],
        ["verify", "--confirmed", "calls", "sms", "notifications", "payments"],
        ["receipts"],
        ["recheck"],
        ["restore", "--all"],
        ["recheck"],
        ["share"],
    ]
    for args in steps:
        rc, out = run_cli(args, env, tmp_path)
        assert rc == 0, (args, out)

    final = json.loads(state.read_text(encoding="utf-8"))
    for name, p in initial["packages"].items():
        assert final["packages"][name]["state"] == p["state"], name
    assert final["settings"]["global"] == initial["settings"]["global"]

    run = sorted((tmp_path / "reports").glob("2*"))[-1]
    for f in ("scan.html", "scan.md", "backup.json", "drill.json", "plan.html", "journal.jsonl", "receipts.html",
              "verify.json", "restore-standalone.sh", "restore-standalone.cmd"):
        assert (run / f).exists(), f
    html = (run / "receipts.html").read_text(encoding="utf-8")
    assert "SIMULATED" in html
    assert "http://" not in html and "https://" not in html  # offline: no external resources
    assert "<script" not in html


def test_help_for_every_command(tmp_path):
    env = dict(os.environ, ADRECEIPTS_HOME=str(tmp_path / "r"))
    from adreceipts.cli import COMMANDS
    for cmd in COMMANDS:
        rc, out = run_cli([cmd, "--help"], env, tmp_path)
        assert rc == 0, cmd
        assert "--adb" in out


def test_missing_adb_gives_clear_error(tmp_path):
    env = dict(os.environ, ADRECEIPTS_HOME=str(tmp_path / "r"), ADRECEIPTS_ADB=str(tmp_path / "no-adb.exe"))
    rc, out = run_cli(["scan"], env, tmp_path)
    assert rc != 0
    assert "adb was not found" in out
    assert "Traceback" not in out


def test_adb_flag_overrides_env(tmp_path):
    state = tmp_path / "phone.json"
    env = dict(os.environ, FAKE_ADB_STATE=str(state), ADRECEIPTS_HOME=str(tmp_path / "r"),
               ADRECEIPTS_ADB=str(tmp_path / "missing"))
    rc, out = run_cli(["doctor", "--adb", str(FAKE)], env, tmp_path)
    assert rc == 0, out


def test_no_command_prints_help(tmp_path):
    rc, out = run_cli([], dict(os.environ, ADRECEIPTS_HOME=str(tmp_path / "r")), tmp_path)
    assert rc != 0
    assert "scan" in out
