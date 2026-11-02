"""Failures undo the batch and stop. Blocked disables never switch method. DNS rolls back."""


def states(device, *names):
    return [device.state["packages"][n]["state"] for n in names]


def test_failed_readback_undoes_batch_and_stops(cli, device):
    device.state["faults"]["readback_ignored"] = ["com.miui.msa.global"]
    cli.prepare("approve")  # analytics then msa, same batch
    rc = cli("apply", "--execute")
    assert rc == 3
    assert "undone" in cli.last_output
    assert states(device, "com.miui.analytics", "com.miui.msa.global") == ["enabled", "enabled"]
    journal = cli.run_dir() / "journal.jsonl"
    assert '"phase": "undone"' in journal.read_text()


def test_failed_health_check_undoes_batch_and_stops(cli, device):
    device.state["faults"]["crash_systemui_on"] = ["com.miui.analytics"]
    cli.prepare("approve", select=("pkg:com.miui.analytics", "pkg:com.miui.daemon"))
    rc = cli("apply", "--execute")
    assert rc == 3
    assert "health check failed" in cli.last_output
    assert "System UI restarted" in cli.last_output
    assert device.state["packages"]["com.miui.analytics"]["state"] == "enabled"


def test_unreachable_phone_stops(cli, device):
    cli.prepare("approve")
    device.state["faults"]["unreachable_after_write"] = True
    device.writes_seen = 0
    rc = cli("apply", "--execute")
    assert rc == 3
    assert "not reachable" in cli.last_output


def test_later_batches_do_not_run_after_a_stop(cli, device):
    device.state["faults"]["readback_ignored"] = ["com.miui.daemon"]
    cli.prepare("approve", select=("pkg:com.miui.daemon", "pkg:com.miui.msa.global"))
    assert cli("apply", "--execute") == 3
    assert device.state["packages"]["com.miui.msa.global"]["state"] == "enabled"
    assert not any(a[-1] == "com.miui.msa.global" and "disable-user" in a for a in device.log)


def test_manufacturer_block_never_switches_method(cli, device):
    device.state["faults"]["blocked_disable"] = ["com.miui.msa.global"]
    cli.prepare("approve")
    rc = cli("apply", "--execute")
    assert rc == 3
    assert "never switches method" in cli.last_output
    assert not any("uninstall" in a for a in device.log)
    assert device.state["packages"]["com.miui.msa.global"]["state"] == "enabled"
    # A new approval is required before anything else runs.
    plan = cli.read("plan.json")
    assert plan["approved"] is None
    m = cli.mark()
    assert cli("apply", "--execute") == 2
    assert cli.writes_since(m) == []


def test_dns_rolls_back_after_failed_check(cli, device):
    device.state["faults"]["dns_fails"] = True
    device.state["settings"]["global"]["private_dns_mode"] = "opportunistic"
    cli("scan")
    cli("backup")
    cli("drill")
    assert cli("plan", "--dns", "adguard", "--approve") == 0
    rc = cli("apply", "--execute")
    assert rc == 3
    assert "previous DNS setting was put back" in cli.last_output
    g = device.state["settings"]["global"]
    assert g.get("private_dns_mode") == "opportunistic"
    assert "private_dns_specifier" not in g


def test_dns_success_then_restore(cli, device):
    cli("scan")
    cli("backup")
    cli("drill")
    assert cli("plan", "--dns", "custom", "--dns-host", "dns.example.org", "--approve") == 0
    assert cli("apply", "--execute") == 0
    assert device.state["settings"]["global"]["private_dns_mode"] == "hostname"
    assert device.state["settings"]["global"]["private_dns_specifier"] == "dns.example.org"
    assert cli("restore", "--all") == 0
    assert device.state["settings"]["global"]["private_dns_mode"] == "off"
    assert "private_dns_specifier" not in device.state["settings"]["global"]


def test_bad_custom_dns_host_refused(cli):
    cli("scan")
    m = cli.mark()
    assert cli("plan", "--dns", "custom", "--dns-host", "x;reboot") == 1
    assert cli.writes_since(m) == []
