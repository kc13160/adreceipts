"""share: no serial, account name, device hash or image by default. Reports never contain secrets."""

import json

import pytest

from adreceipts import share


def all_text(folder):
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in folder.rglob("*") if p.is_file()
                     and p.suffix in (".md", ".html", ".json", ".jsonl", ".sh", ".cmd"))


def test_reports_never_contain_serial(cli, device):
    cli.prepare("approve")
    assert cli("apply", "--execute") == 0
    cli("verify")
    cli("receipts")
    cli("recheck")
    text = all_text(cli.home)
    assert "SIMULATED0001" not in text
    assert device.state["serial"] not in text


def test_share_default_has_no_ids_or_images(cli, device):
    assert cli("scan", "--screenshots", "--consent") == 0
    cli("backup")
    cli("drill")
    cli("plan", "--select", "pkg:com.miui.msa.global", "--approve")
    cli("apply", "--execute")
    cli("receipts", "--screenshots", "--consent")
    run = cli.run_dir()
    dev = json.loads((run / "run.json").read_text())["device"]
    # Plant private data in a report to prove the sanitizer removes it.
    receipts_md = run / "receipts.md"
    receipts_md.write_text(receipts_md.read_text(encoding="utf-8") +
                           "\nowner alice@example.com Account {name=alice.smith, type=com.google}"
                           " IMEI 356938035643809 serialno: SIMULATED0001\n", encoding="utf-8")
    assert cli("share") == 0
    out = sorted(run.glob("share-*"))[-1]
    text = all_text(out)
    assert "<img" not in text
    assert not list(out.rglob("*.png"))
    for secret in (dev["id_hash"], dev["build_hash"], "alice@example.com", "alice.smith", "356938035643809",
                   "SIMULATED0001", str(cli.home.resolve())):
        assert secret not in text, secret
    assert "Image left out" in text


def test_share_with_images_blurs_copies(cli):
    pytest.importorskip("PIL")
    assert cli("scan", "--screenshots", "--consent") == 0
    assert cli("receipts", "--screenshots", "--consent") == 0
    assert cli("share", "--include-images") == 0
    out = sorted(cli.run_dir().glob("share-*"))[-1]
    pngs = sorted(p.name for p in out.rglob("*.png"))
    assert "security_app_recommendations-before.png" in pngs
    html = (out / "receipts.html").read_text(encoding="utf-8")
    assert 'src="screens/security_app_recommendations-before.png"' in html


def test_sanitize_function():
    s = share.sanitize("a@b.co 123456789012345 Account {name=Bob} serial: XYZ123 0123456789abcdef C:/Users/x/r",
                       paths=["C:/Users/x"])
    assert "a@b.co" not in s and "123456789012345" not in s and "Bob" not in s and "XYZ123" not in s
    assert "0123456789abcdef" not in s and "C:/Users/x" not in s
