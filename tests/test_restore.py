"""restore reverses only what the journal recorded."""


def test_restore_only_reverses_journal(cli, device):
    pk = device.state["packages"]
    assert pk["com.android.dreams.basic"]["state"] == "disabled"  # off before AdReceipts
    cli.prepare("approve")
    assert cli("apply", "--execute") == 0
    pk["com.miui.player"]["state"] = "disabled"  # the user turns this off by hand later
    m = cli.mark()
    assert cli("restore", "--all") == 0
    assert pk["com.miui.msa.global"]["state"] == "enabled"
    assert pk["com.miui.analytics"]["state"] == "enabled"
    assert pk["com.android.dreams.basic"]["state"] == "disabled"
    assert pk["com.miui.player"]["state"] == "disabled"
    touched = {a[-1] for a in cli.writes_since(m)}
    assert touched == {"com.miui.msa.global", "com.miui.analytics"}


def test_restore_one_batch(cli, device):
    cli.prepare("approve", select=("pkg:com.miui.daemon", "pkg:com.miui.msa.global"))
    assert cli("apply", "--execute") == 0
    pk = device.state["packages"]
    assert pk["com.miui.daemon"]["state"] == "disabled"
    assert cli("restore", "--batch", "1") == 0
    assert pk["com.miui.daemon"]["state"] == "enabled"
    assert pk["com.miui.msa.global"]["state"] == "disabled"
    assert cli("restore", "--batch", "1") == 0
    assert "Nothing to restore" in cli.last_output
    assert cli("restore", "--batch", "99") == 1


def test_restore_needs_a_choice(cli):
    cli.prepare("approve")
    m = cli.mark()
    assert cli("restore") == 1
    assert cli.writes_since(m) == []


def test_restore_refuses_another_phone(cli, device):
    cli.prepare("approve")
    assert cli("apply", "--execute") == 0
    device.state["serial"] = "SOMEONEELSE"
    m = cli.mark()
    assert cli("restore", "--all") == 2
    assert cli.writes_since(m) == []


def test_restore_works_after_system_update(cli, device):
    cli.prepare("approve")
    assert cli("apply", "--execute") == 0
    device.state["props"]["ro.build.fingerprint"] = "Xiaomi/simulated/simulated:16/SIM2/NEW:user/release-keys"
    assert cli("restore", "--all") == 0
    assert device.state["packages"]["com.miui.msa.global"]["state"] == "enabled"


def test_standalone_scripts_list_only_journal_changes(cli):
    cli.prepare("approve")
    run = cli.run_dir()
    assert "Nothing to restore" in (run / "restore-standalone.sh").read_text()
    assert cli("apply", "--execute") == 0
    sh = (run / "restore-standalone.sh").read_text()
    cmd = (run / "restore-standalone.cmd").read_text()
    assert '"$ADB" shell pm enable --user 0 com.miui.msa.global' in sh
    assert "pm enable --user 0 com.miui.analytics" in cmd
    assert "com.android.dreams.basic" not in sh
    assert "com.android.egg" not in sh  # the drill already undid itself
    assert cli("restore", "--all") == 0
    assert "Nothing to restore" in (run / "restore-standalone.sh").read_text()
