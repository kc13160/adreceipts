"""scan, doctor, recheck, plan (and verify, receipts without screenshots) send no write command."""

import pytest

from adreceipts.adb import Adb, classify
from adreceipts.errors import SafetyStop


@pytest.mark.parametrize("command", [["doctor"], ["scan"], ["plan"], ["recheck"], ["verify"], ["receipts"]])
def test_read_only_commands_send_no_writes(cli, command):
    if command != ["doctor"] and command != ["scan"]:
        assert cli("scan") == 0
    m = cli.mark()
    rc = cli(*command)
    assert rc in (0, 1), cli.last_output
    assert cli.writes_since(m) == []
    assert len(cli.device.log) > m  # it did talk to the phone


def test_read_only_after_changes_still_no_writes(cli):
    cli.prepare("approve")
    assert cli("apply", "--execute") == 0
    m = cli.mark()
    for cmd in (["scan"], ["plan"], ["recheck"], ["doctor"], ["verify"], ["receipts"]):
        cli(*cmd)
    assert cli.writes_since(m) == []


def test_read_level_adb_refuses_write_commands(device):
    adb = Adb(device, "read")
    for args in (["shell", "pm", "disable-user", "--user", "0", "com.miui.msa.global"],
                 ["shell", "settings", "put", "global", "private_dns_mode", "off"],
                 ["shell", "am", "start", "-n", "com.x/.A"],
                 ["exec-out", "screencap", "-p"],
                 ["reboot"], ["install", "x.apk"], ["shell", "rm", "-rf", "/sdcard"]):
        with pytest.raises(SafetyStop):
            adb.run(args)
    assert device.log == []


def test_screen_level_cannot_write(device):
    adb = Adb(device, "screen")
    with pytest.raises(SafetyStop):
        adb.shell("pm", "enable", "--user", "0", "com.android.egg")
    adb.shell("input", "keyevent", "KEYCODE_HOME")
    assert device.log == [["shell", "input", "keyevent", "KEYCODE_HOME"]]


def test_classifier_defaults_to_write_for_unknown():
    assert classify(["shell", "something-new"]) == "write"
    assert classify(["shell", "settings", "get", "global", "x"]) == "read"
    assert classify(["shell", "settings", "put", "global", "x", "y"]) == "write"
    assert classify(["exec-out", "cat", "/sdcard/x"]) == "write"
    assert classify([]) == "write"
