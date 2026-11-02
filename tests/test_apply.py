"""apply: order, approval, dry run, guard before any write, uninstall flags, no way to skip the drill."""

import json

from adreceipts.cli import build_parser


def test_dry_run_writes_nothing(cli):
    cli.prepare("approve")
    m = cli.mark()
    assert cli("apply") == 0
    assert cli.writes_since(m) == []
    assert "Dry run" in cli.last_output
    assert cli.device.state["packages"]["com.miui.msa.global"]["state"] == "enabled"


def test_refuses_without_backup(cli):
    assert cli("scan") == 0
    m = cli.mark()
    assert cli("apply", "--execute") == 2
    assert "No backup" in cli.last_output
    assert cli.writes_since(m) == []


def test_refuses_without_drill(cli):
    cli("scan")
    cli("backup")
    cli("plan", "--select", "pkg:com.miui.msa.global", "--approve")
    m = cli.mark()
    assert cli("apply", "--execute") == 2
    assert "drill" in cli.last_output.lower()
    assert cli.writes_since(m) == []


def test_refuses_failed_drill_file(cli):
    cli.prepare("approve")
    d = cli.run_dir() / "drill.json"
    data = json.loads(d.read_text())
    data["passed"] = False
    d.write_text(json.dumps(data))
    m = cli.mark()
    assert cli("apply", "--execute") == 2
    assert cli.writes_since(m) == []


def test_refuses_without_approval(cli):
    cli.prepare("plan")
    m = cli.mark()
    assert cli("apply", "--execute") == 2
    assert "not approved" in cli.last_output
    assert cli.writes_since(m) == []


def test_changed_selection_clears_approval(cli):
    cli.prepare("approve")
    assert cli("plan", "--select", "pkg:com.miui.daemon") == 0
    m = cli.mark()
    assert cli("apply", "--execute") == 2
    assert cli.writes_since(m) == []


def test_refuses_files_from_another_device(cli, device):
    cli.prepare("approve")
    device.state["serial"] = "OTHERPHONE42"
    m = cli.mark()
    assert cli("apply", "--execute") == 2
    assert "another phone" in cli.last_output
    assert cli.writes_since(m) == []


def test_refuses_after_system_update(cli, device):
    cli.prepare("approve")
    device.state["props"]["ro.build.fingerprint"] = "Xiaomi/simulated/simulated:16/SIM2/OS3.0.302.0:user/release-keys"
    m = cli.mark()
    assert cli("apply", "--execute") == 2
    assert cli.writes_since(m) == []


def test_drill_from_another_run_refused(cli):
    cli.prepare("approve")
    d = cli.run_dir() / "drill.json"
    data = json.loads(d.read_text())
    data["run_id"] = "20000101-000000"
    d.write_text(json.dumps(data))
    m = cli.mark()
    assert cli("apply", "--execute") == 2
    assert cli.writes_since(m) == []


def test_one_refused_package_fails_batch_before_any_write(cli, device):
    cli.prepare("approve")
    # After approval, msa becomes the assistant: guard must refuse the whole plan before writing.
    device.state["roles"]["android.app.role.ASSISTANT"] = ["com.miui.msa.global"]
    m = cli.mark()
    assert cli("apply", "--execute") == 2
    assert "guard refused" in cli.last_output
    assert cli.writes_since(m) == []
    assert device.state["packages"]["com.miui.analytics"]["state"] == "enabled"


def test_no_way_to_skip_the_drill():
    parser = build_parser()
    apply_parser = parser._subparsers._group_actions[0].choices["apply"]
    flags = [opt for act in apply_parser._actions for opt in act.option_strings]
    for flag in flags:
        assert "skip" not in flag and "force" not in flag and "drill" not in flag, flag
    for cmd in ("apply", "plan", "drill"):
        p = parser._subparsers._group_actions[0].choices[cmd]
        for act in p._actions:
            for opt in act.option_strings:
                assert "skip" not in opt and "no-drill" not in opt and "force" not in opt


def test_unknown_skip_flag_is_rejected(cli):
    cli.prepare("approve")
    import pytest
    with pytest.raises(SystemExit):
        cli("apply", "--execute", "--skip-drill")


def test_uninstall_needs_both_flags(cli):
    cli.prepare("approve")
    m = cli.mark()
    assert cli("apply", "--execute", "--method", "uninstall") == 2
    assert "--i-understand-uninstall" in cli.last_output
    assert cli("apply", "--execute", "--i-understand-uninstall") == 2
    assert cli.writes_since(m) == []


def test_uninstall_refuses_non_system_package(cli, device):
    device.state["packages"]["com.miui.msa.global"]["system"] = False
    cli.prepare("approve")
    m = cli.mark()
    assert cli("apply", "--execute", "--method", "uninstall", "--i-understand-uninstall") == 2
    assert "system image" in cli.last_output
    assert cli.writes_since(m) == []


def test_uninstall_refuses_prudent_entries(cli):
    cli.prepare("approve", select=("pkg:com.miui.daemon",))
    m = cli.mark()
    assert cli("apply", "--execute", "--method", "uninstall", "--i-understand-uninstall") == 2
    assert cli.writes_since(m) == []


def test_uninstall_with_both_flags_and_restore(cli, device):
    cli.prepare("approve")
    assert cli("apply", "--execute", "--method", "uninstall", "--i-understand-uninstall") == 0, cli.last_output
    assert device.state["packages"]["com.miui.msa.global"]["state"] == "removed"
    assert ["shell", "pm", "uninstall", "-k", "--user", "0", "com.miui.msa.global"] in device.log
    assert cli("restore", "--all") == 0
    assert device.state["packages"]["com.miui.msa.global"]["state"] == "enabled"
    assert ["shell", "cmd", "package", "install-existing", "--user", "0", "com.miui.msa.global"] in device.log


def test_batches_at_most_five_and_risky_alone():
    from adreceipts.apply import make_batches
    items = [{"kind": "package", "target": "p%d" % i, "risk": "safe"} for i in range(12)]
    items.insert(3, {"kind": "package", "target": "risky", "risk": "prudent"})
    items.append({"kind": "dns", "target": "dns.example.com", "risk": "prudent"})
    batches = make_batches(items)
    assert all(len(b) <= 5 for b in batches)
    assert [b for b in batches if any(i["target"] == "risky" for i in b)] == [[items[3]]]
    assert batches[-1] == [items[-1]]
    assert sum(len(b) for b in batches) == len(items)


def test_journal_written_before_each_change(cli, device, tmp_path):
    cli.prepare("approve")
    journal = cli.run_dir() / "journal.jsonl"
    original = device.handle
    seen = []

    def spy(args):
        if args[:3] == ["shell", "pm", "disable-user"]:
            text = journal.read_text() if journal.exists() else ""
            records = [json.loads(l) for l in text.splitlines()]
            seen.append(any(r.get("phase") == "intent" and r.get("target") == args[-1] for r in records))
        return original(args)

    device.handle = spy
    assert cli("apply", "--execute") == 0
    assert seen and all(seen)
