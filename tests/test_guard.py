"""guard refuses protected entries, prefixes, risky names, role holders, malformed or injected names."""

import pytest

from adreceipts import catalog as cat_mod
from adreceipts import guard
from adreceipts.adb import Adb
from adreceipts.errors import SafetyStop

XIAOMI_PROPS = {"ro.product.brand": "Xiaomi", "ro.mi.os.version.name": "OS3.0"}


@pytest.fixture(scope="module")
def cat():
    return cat_mod.load_for_device(XIAOMI_PROPS)


def protected_lines():
    exact, prefixes = cat_mod.load_protected(cat_mod.default_dir() / "protected.txt")
    return exact, prefixes


def test_every_protected_name_is_refused(cat):
    exact, prefixes = protected_lines()
    assert len(exact) > 50
    for name in exact:
        d = guard.check_package(name, cat)
        assert not d, name


def test_protected_prefixes_are_refused(cat):
    _, prefixes = protected_lines()
    for prefix in prefixes:
        d = guard.check_package(prefix + "anything", cat)
        assert not d, prefix
    assert not guard.check_package("com.android.providers.contacts", cat)
    assert not guard.check_package("com.google.android.gms.policy_sidecar_aps", cat)


def test_required_protected_entries_present():
    exact, prefixes = protected_lines()
    required = """android com.android.systemui com.android.settings com.android.shell com.android.phone
    com.android.server.telecom com.android.packageinstaller com.google.android.packageinstaller
    com.android.permissioncontroller com.google.android.permissioncontroller com.android.nfc com.android.se
    com.android.bluetooth com.android.vending com.google.android.gms com.google.android.gsf
    com.google.android.webview com.android.webview com.android.updater com.miui.home com.miui.securitycore
    com.lbe.security.miui com.xiaomi.finddevice com.xiaomi.xmsf com.miui.gallery com.miui.cloudbackup
    com.miui.backup""".split()
    for name in required:
        assert name in exact, name
    assert "com.android.providers." in prefixes


@pytest.mark.parametrize("name", ["com.example.mybank", "com.acme.wallet", "com.foo.paytm", "com.authy.authy",
                                  "com.x.twofa2fa", "com.miui.PAYMENT"])
def test_risky_name_patterns_refused(cat, name):
    d = guard.check_package(name, cat)
    assert not d
    assert any("never touched" in r or "unknown" in r for r in d.reasons)


def test_risky_pattern_refused_even_if_listed_unless_safe(cat):
    fake = dict(cat.packages)
    cat.packages["com.example.payads"] = {"name": "com.example.payads", "risk": "prudent", "catalog": "x"}
    try:
        assert not guard.check_package("com.example.payads", cat)
        cat.packages["com.example.payads"]["risk"] = "safe"
        assert guard.check_package("com.example.payads", cat)
    finally:
        cat.packages.clear()
        cat.packages.update(fake)


def test_role_holders_refused(cat):
    assert guard.check_package("com.miui.msa.global", cat)
    d = guard.check_package("com.miui.msa.global", cat, held_roles={"com.miui.msa.global"})
    assert not d
    assert "role" in d.reasons[0]


@pytest.mark.parametrize("name", [
    "", "a", "com", ".com.x", "com.x.", "com..x", "1com.x", "com.x;reboot", "com.x && reboot", "com.x|sh",
    "com.x`id`", "com.x$(id)", "com.x\nreboot", "com.x reboot", "../etc/passwd", "com.x/../y", "com.miui.msa.global ",
    "-k", "--user", "com.x'", 'com.x"', "com.ünicode.x", "c" * 300 + ".x", None, 42,
])
def test_malformed_or_injected_names_refused(cat, name):
    d = guard.check_package(name, cat)
    assert not d


def test_unknown_packages_never_offered(cat):
    d = guard.check_package("com.example.adsdk.analytics", cat)
    assert not d
    assert "unknown package" in " ".join(d.reasons)


def test_forbidden_entries_refused(cat):
    assert not guard.check_package("com.miui.securitycenter", cat)


def test_uninstall_rules(cat):
    assert guard.check_package("com.miui.msa.global", cat, method="uninstall", package_info={"system": True})
    assert not guard.check_package("com.miui.msa.global", cat, method="uninstall", package_info={"system": False})
    assert not guard.check_package("com.miui.daemon", cat, method="uninstall", package_info={"system": True})
    assert not guard.check_package("com.miui.msa.global", cat, method="rm")


def test_settings_and_dns_validation(cat):
    assert guard.check_setting("global", "private_dns_mode", "hostname", allow_dns=True)
    assert not guard.check_setting("global", "private_dns_mode", "hostname")  # not declared in catalog
    assert not guard.check_setting("global", "private_dns_mode", "evil", allow_dns=True)
    assert not guard.check_setting("bogus", "x", "1", cat)
    assert not guard.check_setting("global", "x;reboot", "1", cat)
    assert not guard.check_setting("global", "adb_enabled", "0 && reboot", cat)
    assert guard.check_hostname("dns.adguard-dns.com")
    for bad in ("dns", "1.1.1.1", "dns.example.com;reboot", "DNS.Example.com", "-bad.example.com", "a" * 300 + ".com", ""):
        assert not guard.check_hostname(bad), bad


def test_adb_layer_refuses_unsafe_arguments(device):
    adb = Adb(device, "write")
    for bad in ("com.x;reboot", "com.x && id", "a b", "$(id)", "`id`", "x\ny", "x|y", "x>y", "'", '"', "", "x*"):
        with pytest.raises(SafetyStop):
            adb.shell("pm", "disable-user", "--user", "0", bad)
    assert device.log == []


def test_require_batch_fails_whole_batch(cat):
    items = [{"kind": "package", "target": "com.miui.msa.global"},
             {"kind": "package", "target": "com.miui.securitycenter"}]
    with pytest.raises(SafetyStop) as exc:
        guard.require_batch(items, cat, set())
    assert "com.miui.securitycenter" in exc.value.message
