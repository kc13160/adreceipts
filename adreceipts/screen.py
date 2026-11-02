"""Screen evidence: only with --screenshots and explicit consent.

Privacy rules enforced here:
  - only surfaces listed in the catalog with `capture: true`, opened by the tool;
  - never banking, password, messaging, email, gallery, browser or settings screens;
  - the foreground app is read before each capture, and the capture is aborted
    unless it is the surface's own app;
  - UI text is searched for ad words and only the matched words are kept;
  - images stay in the local, git-ignored reports folder.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import device

SENSITIVE_WORDS = (
    "bank", "pay", "wallet", "auth", "2fa", "password", "pass", "keychain", "vault",
    "mms", "messag", "sms", "mail", "gallery", "photo", "camera", "browser", "chrome", "firefox",
    "contacts", "dialer", "settings", "notes", "files", "fileexplorer", "documents", "downloads",
)
COMPONENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.]*/[A-Za-z0-9_.]+$")
AD_WORDS = re.compile(r"(?<![A-Za-z])(Ad|Ads|AD|ADS|Sponsored|Advertisement|Promoted|广告)(?![A-Za-z])")
TEXT_ATTR = re.compile(r'(?:text|content-desc)="([^"]{1,200})"')
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

CONSENT_TEXT = """\
Screenshots are OFF unless you agree.

If you agree, AdReceipts will open only the catalog screens marked as safe to
capture (for example the Security and Themes apps), check that the right app is
on screen, and save a screenshot plus the ad words it finds. It never captures
banking, password, messaging, email, gallery, browser or settings screens.

Images are stored only on this computer, in the reports folder, which git
ignores. If you ask a hosted AI agent to look at them, they are sent to that
agent's provider.

To agree, run the same command again with: --screenshots --consent
"""


def sensitive(package):
    low = (package or "").lower()
    return any(w in low for w in SENSITIVE_WORDS)


def capture_allowed(surface):
    app = surface.get("app")
    if not surface.get("capture"):
        return False, "screenshots are not enabled for this surface in the catalog"
    if not app:
        return False, "no app is linked to this surface"
    if sensitive(app):
        return False, "this app may show private information"
    return True, ""


def _resolve_component(adb, surface):
    comp = surface.get("open")
    if comp:
        return comp if COMPONENT_RE.match(comp) else None
    res = adb.shell("cmd", "package", "resolve-activity", "--brief", "-c", "android.intent.category.LAUNCHER", surface["app"])
    lines = [l.strip() for l in res.text.splitlines() if "/" in l]
    if not lines:
        return None
    comp = lines[-1]
    if not comp.startswith(surface["app"] + "/"):
        return None
    return comp if COMPONENT_RE.match(comp) else None


def ad_words(ui_xml):
    found = []
    for text in TEXT_ATTR.findall(ui_xml):
        for m in AD_WORDS.findall(text):
            if m not in found:
                found.append(m)
    return found


def capture_surface(adb, surface, out_dir, tag, sleep):
    """Open one surface and collect evidence. Returns an evidence dict."""
    ev = {"surface": surface["id"], "checked": False, "ad_seen": None, "ad_words": [], "image": None, "note": ""}
    allowed, why = capture_allowed(surface)
    if not allowed:
        ev["note"] = why
        return ev
    app = surface["app"]
    states = device.package_states(adb)
    if states.get(app, {}).get("state") != "enabled":
        ev["note"] = "the app is not enabled, so its screen was not opened"
        return ev
    comp = _resolve_component(adb, surface)
    if not comp:
        ev["note"] = "could not find how to open this screen"
        return ev
    adb.shell("am", "start", "-n", comp)
    sleep(3)
    try:
        if device.foreground(adb) != app:
            ev["note"] = "capture aborted: another app was on screen"
            return ev
        ui = adb.exec_out("uiautomator", "dump", "/dev/tty", timeout=60).text
        words = ad_words(ui)
        if device.foreground(adb) != app:
            ev["note"] = "capture aborted: another app was on screen"
            return ev
        shot = adb.exec_out("screencap", "-p", timeout=60).out
        ev["checked"] = True
        ev["ad_words"] = words
        ev["ad_seen"] = bool(words)
        if shot.startswith(PNG_MAGIC):
            rel = Path("screens") / ("%s-%s.png" % (surface["id"], tag))
            target = Path(out_dir) / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(shot)
            ev["image"] = rel.as_posix()
        else:
            ev["note"] = "the screenshot could not be read"
        return ev
    finally:
        adb.shell("input", "keyevent", "KEYCODE_HOME")
