"""The undo drill: harmless candidate, read-back both ways, tied to the phone."""


def test_drill_needs_backup(cli):
    cli("scan")
    m = cli.mark()
    assert cli("drill") == 2
    assert cli.writes_since(m) == []


def test_drill_passes_and_restores(cli, device):
    cli("scan")
    cli("backup")
    assert cli("drill") == 0
    d = cli.read("drill.json")
    assert d["passed"] is True
    assert d["package"] == "com.android.egg"
    assert device.state["packages"]["com.android.egg"]["state"] == "enabled"
    assert "id_hash" in d["device"]


def test_drill_skips_foreground_and_role_holders(cli, device):
    device.state["foreground"] = "com.android.egg"
    cli("scan")
    cli("backup")
    assert cli("drill") == 0
    assert cli.read("drill.json")["package"] == "com.android.printservice.recommendation"


def test_no_safe_candidate_stops(cli, device):
    for n in ("com.android.egg", "com.android.printservice.recommendation"):
        device.state["packages"][n]["state"] = "disabled"
    cli("scan")
    cli("backup")
    m = cli.mark()
    assert cli("drill") == 2
    assert "scan-only" in cli.last_output
    assert cli.writes_since(m) == []
    assert cli.read("drill.json")["passed"] is False


def test_drill_fails_when_undo_does_not_work(cli, device):
    device.state["faults"]["enable_ignored"] = ["com.android.egg"]
    cli("scan")
    cli("backup")
    assert cli("drill") == 3
    assert "Undo did not work" in cli.last_output
    assert cli.read("drill.json")["passed"] is False


def test_drill_fails_when_disable_blocked(cli, device):
    device.state["faults"]["blocked_disable"] = ["com.android.egg"]
    cli("scan")
    cli("backup")
    assert cli("drill") == 3
    assert not any("uninstall" in a for a in device.log)
    assert cli.read("drill.json")["passed"] is False
