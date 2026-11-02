"""Regression tests for the findings of the fresh-eyes safety review (see REPORT.md)."""

import json

import pytest

from adreceipts.errors import AdbError


def ready_for_dns(cli):
    cli("scan")
    cli("backup")
    assert cli("drill") == 0


def test_dns_rollback_restores_mixed_case_specifier(cli, device):
    g = device.state["settings"]["global"]
    g["private_dns_mode"] = "hostname"
    g["private_dns_specifier"] = "Dns.Example.org"
    device.state["faults"]["dns_fails"] = True
    ready_for_dns(cli)
    assert cli("plan", "--dns", "adguard", "--approve") == 0
    assert cli("apply", "--execute") == 3
    assert g["private_dns_mode"] == "hostname"
    assert g["private_dns_specifier"] == "Dns.Example.org"


def test_dns_not_changed_when_old_value_unsafe(cli, device):
    g = device.state["settings"]["global"]
    g["private_dns_mode"] = "hostname"
    g["private_dns_specifier"] = "bad$value"
    ready_for_dns(cli)
    assert cli("plan", "--dns", "adguard", "--approve") == 0
    m = cli.mark()
    assert cli("apply", "--execute") == 3
    assert "could not put back safely" in cli.last_output
    assert cli.writes_since(m) == []
    assert g["private_dns_specifier"] == "bad$value"


def test_adb_failure_mid_batch_undoes_batch(cli, device):
    cli.prepare("approve")  # analytics, msa in one batch
    original = device.handle

    def flaky(args):
        if args[:3] == ["shell", "pm", "disable-user"] and args[-1] == "com.miui.msa.global":
            raise AdbError("adb did not answer within 30 seconds")
        return original(args)

    device.handle = flaky
    assert cli("apply", "--execute") == 3
    assert "restore --all" in cli.last_output
    assert device.state["packages"]["com.miui.analytics"]["state"] == "enabled"


def test_scripts_written_before_the_change(cli, device):
    cli.prepare("approve")
    script = cli.run_dir() / "restore-standalone.sh"
    original = device.handle
    seen = []

    def spy(args):
        if args[:3] == ["shell", "pm", "disable-user"]:
            seen.append("pm enable --user 0 %s" % args[-1] in script.read_text())
        return original(args)

    device.handle = spy
    assert cli("apply", "--execute") == 0
    assert seen and all(seen)


def test_restore_all_finds_changes_from_earlier_runs(cli, device):
    cli.prepare("approve")
    assert cli("apply", "--execute") == 0
    assert cli("scan") == 0  # starts a new run
    assert cli("restore", "--all") == 0
    assert device.state["packages"]["com.miui.msa.global"]["state"] == "enabled"
    assert device.state["packages"]["com.miui.analytics"]["state"] == "enabled"


def test_restore_refuses_undeclared_setting_from_edited_journal(cli, device):
    cli.prepare("approve")
    assert cli("apply", "--execute") == 0
    journal = cli.run_dir() / "journal.jsonl"
    with open(journal, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": 99, "phase": "intent", "batch": "9", "op": "setting", "target": "global/adb_enabled",
                             "namespace": "global", "key": "adb_enabled", "before": {"value": "0"}}) + "\n")
    m = cli.mark()
    assert cli("restore", "--all") == 3
    assert "refused by guard" in cli.last_output
    assert not any("adb_enabled" in a for a in cli.writes_since(m))


def test_damaged_last_journal_line_is_tolerated(cli, device):
    cli.prepare("approve")
    assert cli("apply", "--execute") == 0
    journal = cli.run_dir() / "journal.jsonl"
    with open(journal, "a", encoding="utf-8") as fh:
        fh.write('{"id": 50, "phase": "inte')
    assert cli("restore", "--all") == 0
    assert device.state["packages"]["com.miui.msa.global"]["state"] == "enabled"


def test_user_apps_not_listed_as_unknown(cli, device):
    device.state["packages"]["com.glow.period.tracker"] = {"system": False, "state": "enabled"}
    assert cli("scan") == 0
    text = (cli.run_dir() / "scan.md").read_text(encoding="utf-8") + (cli.run_dir() / "scan.json").read_text()
    assert "period.tracker" not in text
    assert "com.example.adsdk.analytics" not in text
    assert "com.google.android.adservices.api" in text  # system package, reported only


def test_share_removes_custom_dns_host(cli, device):
    g = device.state["settings"]["global"]
    g["private_dns_mode"] = "hostname"
    g["private_dns_specifier"] = "a1b2c3.dns.nextdns.io"
    assert cli("scan") == 0
    assert "a1b2c3" in (cli.run_dir() / "scan.md").read_text(encoding="utf-8")
    assert cli("share") == 0
    out = sorted(cli.run_dir().glob("share-*"))[-1]
    assert "a1b2c3" not in (out / "scan.md").read_text(encoding="utf-8")


def test_data_folder_is_git_ignored(cli):
    cli("scan")
    assert (cli.home / ".gitignore").read_text().strip().endswith("*")


@pytest.mark.parametrize("serial", ["", "unknown", "0123456789ABCDEF"])
def test_placeholder_serial_refused(cli, device, serial):
    device.state["serial"] = serial
    assert cli("scan") == 2
    assert "unique ID" in cli.last_output


def test_failed_package_list_stops_instead_of_guessing(cli, device):
    cli.prepare("approve")
    original = device.handle

    def broken(args):
        if args[:4] == ["shell", "pm", "list", "packages"] and "-d" in args:
            return 1, "", "Error: could not access the package manager"
        return original(args)

    device.handle = broken
    m = cli.mark()
    assert cli("apply", "--execute") == 4
    assert cli.writes_since(m) == []


def test_unreadable_roles_block_apply(cli, device):
    cli.prepare("approve")
    original = device.handle

    def no_roles(args):
        if args[:3] == ["shell", "cmd", "role"]:
            return 255, "Unknown command: role", ""
        return original(args)

    device.handle = no_roles
    m = cli.mark()
    assert cli("apply", "--execute") == 2
    assert "role holders could not be read" in cli.last_output
    assert cli.writes_since(m) == []


def test_capture_aborted_when_another_window_has_focus(cli, device):
    device.state["focus_override"] = "com.android.systemui"
    assert cli("scan", "--screenshots", "--consent") == 0
    assert not any(a[:2] == ["exec-out", "screencap"] for a in device.log)
    assert not any(a[:2] == ["exec-out", "uiautomator"] for a in device.log)
