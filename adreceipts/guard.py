"""guard: the last check before any write. Every package and setting goes through it.

A refusal is final for the batch: one refused item fails the whole batch
before anything is written.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .errors import SafetyStop

PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")
RISKY_WORDS = ("bank", "wallet", "pay", "auth", "2fa")
NAMESPACES = ("system", "secure", "global")
SETTING_KEY_RE = re.compile(r"^[A-Za-z0-9_.]{1,100}$")
SETTING_VALUE_RE = re.compile(r"^[A-Za-z0-9_.:@-]{0,253}$")
HOSTNAME_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
# Settings AdReceipts itself may write for the DNS option.
DNS_KEYS = ("private_dns_mode", "private_dns_specifier")
DNS_MODES = ("off", "opportunistic", "hostname")


@dataclass
class Decision:
    ok: bool
    reasons: list = field(default_factory=list)

    def __bool__(self):
        return self.ok


def valid_package_name(name):
    return isinstance(name, str) and len(name) <= 255 and bool(PACKAGE_RE.match(name))


def check_package(name, catalog, held_roles=(), purpose="apply", method="disable", foreground=None, package_info=None):
    """Decide whether `name` may be changed. Never raises; returns a Decision."""
    reasons = []
    if not valid_package_name(name):
        return Decision(False, ["malformed package name %r" % (name,)])
    if catalog.is_protected(name):
        reasons.append("protected (catalog/protected.txt)")
    entry = catalog.packages.get(name)
    lowered = name.lower()
    risky = [w for w in RISKY_WORDS if w in lowered]
    if risky and not (entry and entry.get("risk") == "safe"):
        reasons.append("name contains %r (banking, payment or login apps are never touched)" % risky[0])
    if name in set(held_roles):
        reasons.append("holds a role right now (home, phone, SMS, browser, assistant, keyboard, WebView, admin or accessibility)")
    if purpose == "drill":
        if name not in [d["name"] for d in catalog.drill_candidates]:
            reasons.append("not a listed drill candidate")
        if foreground and name == foreground:
            reasons.append("currently on screen")
    else:
        if entry is None:
            reasons.append("unknown package: not in the catalog, so it is never offered")
        else:
            risk = entry.get("risk")
            if risk == "forbidden":
                reasons.append("rated 'forbidden' in the catalog")
            if method == "uninstall":
                if risk != "safe":
                    reasons.append("uninstall is only allowed for 'safe' entries (this one is %r)" % risk)
                if package_info is not None and not package_info.get("system"):
                    reasons.append("not part of the system image, so uninstall could not be undone")
            elif method != "disable":
                reasons.append("unknown method %r" % (method,))
    return Decision(not reasons, reasons)


def check_setting(namespace, key, value, catalog=None, allow_dns=False):
    reasons = []
    if namespace not in NAMESPACES:
        reasons.append("unknown settings namespace %r" % (namespace,))
    if not isinstance(key, str) or not SETTING_KEY_RE.match(key):
        reasons.append("malformed setting name %r" % (key,))
    if value is not None and (not isinstance(value, str) or not SETTING_VALUE_RE.match(value)):
        reasons.append("malformed setting value %r" % (value,))
    if not reasons:
        known = False
        if allow_dns and namespace == "global" and key in DNS_KEYS:
            known = True
            if key == "private_dns_mode" and value not in DNS_MODES + (None,):
                reasons.append("private_dns_mode must be one of %s" % ", ".join(DNS_MODES))
            if key == "private_dns_specifier" and value is not None and value != "" and not HOSTNAME_RE.match(value):
                reasons.append("not a valid DNS hostname: %r" % value)
        elif catalog is not None:
            for s in catalog.surfaces.values():
                st = s.get("turn_off", {}).get("setting")
                if st and st["namespace"] == namespace and st["key"] == key:
                    known = True
        if not known:
            reasons.append("setting %s/%s is not declared in the catalog" % (namespace, key))
    return Decision(not reasons, reasons)


def check_hostname(host):
    if not isinstance(host, str) or not HOSTNAME_RE.match(host):
        return Decision(False, ["not a valid DNS hostname: %r" % (host,)])
    return Decision(True, [])


def require_batch(items, catalog, held_roles, method="disable", states=None):
    """Check every item of a batch. Raise before any write if one is refused."""
    refused = []
    for item in items:
        if item["kind"] == "package":
            info = (states or {}).get(item["target"])
            d = check_package(item["target"], catalog, held_roles, method=method, package_info=info)
        elif item["kind"] == "setting":
            d = check_setting(item["namespace"], item["key"], item["value"], catalog)
        elif item["kind"] == "dns":
            d = check_hostname(item["target"])
        else:
            d = Decision(False, ["unknown item kind"])
        if not d:
            refused.append("%s: %s" % (item.get("target"), "; ".join(d.reasons)))
    if refused:
        raise SafetyStop(
            "guard refused this batch, so nothing in it was changed:\n  - " + "\n  - ".join(refused),
            hint="Run plan again to see what can be changed.",
        )
