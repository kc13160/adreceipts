"""Screenshots are off by default, need consent, and are refused on a non-matching foreground app."""

from adreceipts import screen


def screen_cmds(log):
    return [a for a in log if a[:2] in (["shell", "am"], ["exec-out", "screencap"], ["exec-out", "uiautomator"])
            or a[:2] == ["shell", "input"]]


def test_scan_takes_no_screenshots_by_default(cli, device):
    assert cli("scan") == 0
    assert screen_cmds(device.log) == []
    assert not (cli.run_dir() / "screens").exists()


def test_screenshots_need_consent(cli, device):
    assert cli("scan", "--screenshots") == 2
    assert "To agree" in cli.last_output
    assert device.log == []


def test_screenshots_with_consent_only_on_allowed_surfaces(cli, device):
    assert cli("scan", "--screenshots", "--consent") == 0
    opened = [a[4].split("/")[0] for a in device.log if a[:3] == ["shell", "am", "start"]]
    assert opened, "some catalog surface should be opened"
    for pkg in opened:
        assert not screen.sensitive(pkg), pkg
    assert set(opened) <= {"com.miui.securitycenter", "com.android.thememanager"}
    shots = list((cli.run_dir() / "screens").glob("*.png"))
    assert shots
    scan = cli.read("scan.json")
    assert scan["evidence"]["surfaces"]["security_app_recommendations"]["labels"] == ["ad seen"]


def test_capture_aborted_when_foreground_does_not_match(cli, device):
    device.state["faults"]["foreground_stuck"] = "com.example.mybank"
    assert cli("scan", "--screenshots", "--consent") == 0
    assert not any(a[:2] == ["exec-out", "screencap"] for a in device.log)
    assert not any(a[:2] == ["exec-out", "uiautomator"] for a in device.log)
    scan = cli.read("scan.json")
    notes = [e.get("note", "") for e in scan["evidence"]["screens"].values()]
    assert any("aborted" in n for n in notes)
    assert "mybank" not in (cli.run_dir() / "scan.json").read_text()


def test_sensitive_apps_never_captured():
    for pkg in ("com.mi.globalbrowser", "com.android.settings", "com.miui.gallery", "com.google.android.gm",
                "com.android.mms", "com.example.mybank", "com.google.android.apps.authenticator2",
                "com.android.providers.downloads.ui", "com.google.android.apps.messaging"):
        ok, _ = screen.capture_allowed({"id": "x", "app": pkg, "capture": True})
        assert not ok, pkg


def test_capture_requires_catalog_flag():
    ok, why = screen.capture_allowed({"id": "x", "app": "com.android.thememanager"})
    assert not ok
    ok, _ = screen.capture_allowed({"id": "x", "app": "com.android.thememanager", "capture": True})
    assert ok


def test_only_ad_words_are_kept():
    xml = '<node text="Hello Alice" /><node text="Ad" /><node content-desc="Sponsored offer"/><node text="Address"/>'
    assert screen.ad_words(xml) == ["Ad", "Sponsored"]


def test_receipts_without_ad_before_say_not_proven(cli, device):
    cli.prepare("approve")
    assert cli("apply", "--execute") == 0
    assert cli("receipts") == 0
    rec = cli.read("receipts.json")
    for sid, r in rec["surfaces"].items():
        assert r["outcome"] == "not proven", sid
    html = (cli.run_dir() / "receipts.html").read_text(encoding="utf-8")
    assert "b-removed" not in html
    assert "not proven" in html


def test_receipts_with_screens_before_and_after(cli, device):
    assert cli("scan", "--screenshots", "--consent") == 0
    cli("backup")
    cli("drill")
    cli("plan", "--select", "pkg:com.miui.msa.global", "--approve")
    assert cli("apply", "--execute") == 0
    assert cli("receipts", "--screenshots", "--consent") == 0
    rec = cli.read("receipts.json")
    assert rec["surfaces"]["security_app_recommendations"]["outcome"] == "ad not seen after change"
    assert rec["surfaces"]["themes_ads"]["outcome"] == "ad not seen after change"
    assert rec["surfaces"]["music_ads"]["outcome"] == "not proven"
    html = (cli.run_dir() / "receipts.html").read_text(encoding="utf-8")
    assert "screens/security_app_recommendations-before.png" in html
    assert "screens/security_app_recommendations-after.png" in html
    assert "SIMULATED" in html
