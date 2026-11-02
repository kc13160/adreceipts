"""Collecting read-only evidence about ad sources, used by scan, receipts and recheck.

Honest labels only:
  ad seen | ad setting on | ad service active | not seen at scan time | not checked
There is never a single score or a "clean" verdict.
"""

from __future__ import annotations

import re

from . import device, screen

AD_SEEN = "ad seen"
SETTING_ON = "ad setting on"
SERVICE_ACTIVE = "ad service active"
NOT_SEEN = "not seen at scan time"
NOT_CHECKED = "not checked"
LABELS = (AD_SEEN, SETTING_ON, SERVICE_ACTIVE, NOT_SEEN, NOT_CHECKED)

ADLIKE = re.compile(r"(^|\.)(ads?|adservices?|adsolution\w*|adsdk|admob|analytics|advert\w*|tracking|tracker\w*|promo\w*|msa)(\.|$)", re.I)


def is_service(pkg):
    """An ad or tracking service. Host apps rated 'forbidden' (Security, Downloads) are not."""
    return pkg["category"] in ("ads", "tracking") and pkg["risk"] != "forbidden"


def package_label(pkg):
    if pkg["risk"] == "forbidden":
        return "host app, never changed"
    if pkg["state"] != "enabled":
        return NOT_SEEN
    return SERVICE_ACTIVE if is_service(pkg) else "app with ads, on"


def unknown_adlike(states, catalog):
    out = []
    for name in sorted(states):
        # System packages only: apps the user installed stay out of reports (they can be private).
        if name in catalog.packages or not states[name].get("system"):
            continue
        if ADLIKE.search(name):
            out.append(name)
    return out


def collect(adb, catalog, screens=None):
    """Read package states, settings and (optionally) screen evidence."""
    states = device.package_states(adb)
    packages, absent = {}, []
    for name, entry in sorted(catalog.packages.items()):
        st = states.get(name)
        if not st:
            absent.append(name)
            continue
        packages[name] = {
            "state": st["state"],
            "system": st["system"],
            "category": entry["category"],
            "risk": entry["risk"],
            "role": entry["role"],
            "proof": entry["proof"],
            "catalog": entry["catalog"],
        }
    settings = {}
    for sid, s in catalog.surfaces.items():
        st = s["turn_off"].get("setting")
        if st:
            settings[sid] = device.setting(adb, st["namespace"], st["key"])
    info = {}
    for chk in catalog.info_checks:
        info[chk["id"]] = device.setting(adb, chk["namespace"], chk["key"])
    screens = screens or {}
    surfaces = {}
    for sid, s in catalog.surfaces.items():
        labels, details = [], []
        st = s["turn_off"].get("setting")
        if st and sid in settings:
            value = settings[sid]
            if value is not None and value in st["on_values"]:
                labels.append(SETTING_ON)
                details.append("setting %s is %s" % (st["key"], value))
            else:
                details.append("setting %s is %s" % (st["key"], value if value is not None else "not set"))
        related = [n for n in catalog.packages_for_surface(sid) if n in packages]
        active = [n for n in related if packages[n]["state"] == "enabled" and is_service(packages[n])]
        if active:
            labels.append(SERVICE_ACTIVE)
            details.extend("%s is on" % n for n in active)
        for n in related:
            if packages[n]["state"] != "enabled":
                details.append("%s is %s" % (n, packages[n]["state"]))
        app = s.get("app")
        if app and app not in states and not related:
            details.append("the app for this location is not on this phone")
        ev = screens.get(sid)
        if ev and ev.get("checked"):
            if ev.get("ad_seen"):
                labels.append(AD_SEEN)
                details.append("ad words on screen: %s" % ", ".join(ev["ad_words"]))
            else:
                labels.append(NOT_SEEN)
                details.append("screen opened, no ad words found at that moment")
        else:
            labels.append(NOT_CHECKED)
            if ev and ev.get("note"):
                details.append("screen: %s" % ev["note"])
        surfaces[sid] = {"labels": labels, "details": details, "present": bool(related) or (app in states if app else True)}
    return {
        "packages": packages,
        "absent": absent,
        "settings": settings,
        "info": info,
        "surfaces": surfaces,
        "screens": screens,
        "unknown_adlike": unknown_adlike(states, catalog),
    }


def capture_all(adb, catalog, out_dir, tag, sleep):
    """Screen evidence for every catalog surface that allows it."""
    screens = {}
    for sid, s in catalog.surfaces.items():
        ok, why = screen.capture_allowed(s)
        if not ok:
            screens[sid] = {"surface": sid, "checked": False, "note": why}
            continue
        screens[sid] = screen.capture_surface(adb, s, out_dir, tag, sleep)
    return screens
