"""Private DNS ad filtering: optional, never on by default, rolled back on failure.

The DNS provider sees every domain name the phone looks up. The user picks a
provider from the short sourced list in the catalog, or their own hostname.
"""

from __future__ import annotations

import re

from . import device
from .guard import check_hostname
from .ops import reverse

# A domain Android itself uses for connectivity checks; ad filters do not block it.
TEST_HOST = "connectivitycheck.gstatic.com"
RESOLVED = re.compile(r"^PING \S+ \((\d+\.\d+\.\d+\.\d+|[0-9a-fA-F:]+)\)", re.M)


def resolves(adb, host=TEST_HOST):
    res = adb.shell("ping", "-c", "1", "-W", "5", host, timeout=20)
    text = res.text + res.err_text
    if "unknown host" in text.lower() or "bad address" in text.lower():
        return False
    return bool(RESOLVED.search(text))


def set_private_dns(ctx, batch, host, tries=3, wait=3):
    """Returns (status, detail). status: done | skipped | failed (rolled back)."""
    if not check_hostname(host):
        return "failed", "not a valid DNS hostname"
    before = {
        "mode": device.setting(ctx.adb, "global", "private_dns_mode"),
        "specifier": device.setting(ctx.adb, "global", "private_dns_specifier"),
    }
    if before["mode"] == "hostname" and before["specifier"] == host:
        return "skipped", "already set to %s" % host
    cid = ctx.journal.intent(batch, "dns", host, before)
    ctx.adb.shell("settings", "put", "global", "private_dns_specifier", host)
    ctx.adb.shell("settings", "put", "global", "private_dns_mode", "hostname")
    mode = device.setting(ctx.adb, "global", "private_dns_mode")
    spec = device.setting(ctx.adb, "global", "private_dns_specifier")
    ok = mode == "hostname" and spec == host
    if ok:
        ok = False
        for _ in range(tries):
            ctx.sleep(wait)
            if resolves(ctx.adb):
                ok = True
                break
    change = ctx.journal.changes()[cid]
    if ok:
        ctx.journal.mark(cid, "done", after={"mode": mode, "specifier": spec})
        return "done", "Private DNS set to %s; name lookups still work" % host
    ctx.journal.mark(cid, "failed", after={"mode": mode, "specifier": spec}, note="lookup test failed")
    back, detail = reverse(ctx, ctx.journal.changes()[cid] or change, "undone")
    if back:
        return "failed", "name lookups failed with %s, so the previous DNS setting was put back" % host
    return "failed", "name lookups failed with %s and putting the old setting back also failed (%s)" % (host, detail)
