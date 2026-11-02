"""Managed phones, work profiles, several devices and unauthorized phones stop the run."""

import pytest


@pytest.mark.parametrize("flag", ["work_profile", "device_owner", "profile_owner"])
@pytest.mark.parametrize("command", [["scan"], ["doctor"]])
def test_managed_phone_stops(cli, device, flag, command):
    device.state[flag] = True
    rc = cli(*command)
    assert rc == 2
    assert "managed" in cli.last_output.lower() or "work" in cli.last_output.lower()
    assert cli.writes_since(0) == []


def test_managed_detected_before_apply(cli, device):
    cli.prepare("approve")
    device.state["work_profile"] = True
    m = cli.mark()
    assert cli("apply", "--execute") == 2
    assert cli.writes_since(m) == []


def test_several_devices_refused(cli, device):
    device.state["devices"] = ["device", "device"]
    assert cli("scan") == 2
    assert "exactly one" in cli.last_output


def test_unauthorized_phone(cli, device):
    device.state["devices"] = ["unauthorized"]
    assert cli("scan") == 4
    assert "authorized" in cli.last_output


def test_no_phone(cli, device):
    device.state["devices"] = []
    assert cli("doctor") == 1
    assert cli("scan") == 4
