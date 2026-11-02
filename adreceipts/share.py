"""share: a sanitized copy of a run's reports, safe to post.

Removes device hashes, account names, email addresses, long numbers (IMEI,
serial-like strings) and local paths. Images are left out unless the user
reviewed them and passes --include-images; then the status bar is blurred,
which needs the optional Pillow extra (pip install Pillow).
"""

from __future__ import annotations

import datetime as _dt
import re
from pathlib import Path

from . import catalog as _catalog
from . import yamlite
from .errors import AdReceiptsError
from .journal import Journal
from .store import read_json, write_text

SHAREABLE = re.compile(r"^(scan|plan|receipts|recheck-[0-9-]+)\.(md|html)$")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LONG_NUMBER = re.compile(r"(?<![0-9])[0-9]{12,20}(?![0-9])")
ACCOUNT = re.compile(r"(Account\s*\{\s*name=)[^,}]*", re.I)
SERIALISH = re.compile(r"\b(serial(?:no|_number| number)?\s*[:=]\s*)\S+", re.I)
IMG_TAG = re.compile(r"<img\b[^>]*>", re.I)
MD_IMAGE = re.compile(r"\(image: `[^`]*`\)")
HEX_HASH = re.compile(r"\b[0-9a-f]{16}\b")
STATUS_BAR_SHARE = 0.10


def sanitize(text, secrets_to_remove=(), paths=()):
    for secret in secrets_to_remove:
        if secret:
            text = text.replace(secret, "[removed]")
    for p in paths:
        if p:
            text = text.replace(p, "[local path]")
            text = text.replace(p.replace("\\", "/"), "[local path]")
    text = EMAIL.sub("[email removed]", text)
    text = ACCOUNT.sub(r"\1[removed]", text)
    text = SERIALISH.sub(r"\1[removed]", text)
    text = LONG_NUMBER.sub("[number removed]", text)
    text = HEX_HASH.sub("[id removed]", text)
    return text


def known_dns_hosts(catalog_dir=None):
    hosts = set()
    for path in _catalog.catalog_files(catalog_dir or _catalog.default_dir()):
        try:
            data = yamlite.load_file(str(path)) or {}
        except yamlite.YamlError:
            continue
        hosts.update(p.get("hostname") for p in data.get("dns_providers", []) or [])
    return hosts


def custom_dns_hosts(run_dir, catalog_dir=None):
    """Private DNS hostnames that are not catalog providers. They can carry a personal account ID."""
    found = set()
    scan = read_json(run_dir / "scan.json") or {}
    found.add(((scan.get("evidence") or {}).get("info") or {}).get("private_dns_specifier"))
    backup = read_json(run_dir / "backup.json") or {}
    found.add((backup.get("settings") or {}).get("global/private_dns_specifier"))
    plan = read_json(run_dir / "plan.json") or {}
    found.update(i.get("target") for i in plan.get("items", []) if i.get("kind") == "dns")
    for c in Journal(run_dir).changes().values():
        if c.get("op") == "dns":
            found.add(c.get("target"))
            found.add((c.get("before") or {}).get("specifier"))
            found.add((c.get("after") or {}).get("specifier"))
    found.discard(None)
    found.discard("")
    return sorted(found - known_dns_hosts(catalog_dir), key=len, reverse=True)


def blur_status_bar(src, dst):
    try:
        from PIL import Image, ImageFilter  # optional extra
    except ImportError:
        raise AdReceiptsError("Including images needs the optional Pillow package to blur the status bar.",
                              hint="pip install Pillow, or share without --include-images.")
    with Image.open(src) as im:
        im = im.convert("RGB")
        h = max(1, int(im.height * STATUS_BAR_SHARE))
        top = im.crop((0, 0, im.width, h)).filter(ImageFilter.GaussianBlur(radius=12))
        im.paste(top, (0, 0))
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, format="PNG")


def run(app):
    args = app.args
    run_id, run_dir = app.run()
    info = read_json(run_dir / "run.json") or {}
    dev = info.get("device", {})
    secrets_to_remove = [dev.get("id_hash"), dev.get("build_hash")] + custom_dns_hosts(run_dir, app.catalog_dir)
    paths = [str(run_dir.resolve()), str(app.home.resolve()), str(Path.home())]
    out = run_dir / ("share-%s" % _dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    files = sorted(p for p in run_dir.iterdir() if p.is_file() and SHAREABLE.match(p.name))
    if not files:
        raise AdReceiptsError("No report to share in this run.", hint="Run scan (and receipts) first.")
    images = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        if f.suffix == ".html":
            if args.include_images:
                for src in re.findall(r'<img src="(screens/[A-Za-z0-9_.-]+\.png)"', text):
                    blur_status_bar(run_dir / src, out / src)
                    images += 1
            else:
                text = IMG_TAG.sub('<div class="placeholder">Image left out of the shared copy</div>', text)
        else:
            if not args.include_images:
                text = MD_IMAGE.sub("(image left out)", text)
        write_text(out / f.name, sanitize(text, secrets_to_remove, paths))
    app.say("Sanitized copy written: %s" % out,
            "Removed: device IDs, account names, email addresses, long numbers, local paths, custom DNS hosts.")
    if args.include_images:
        app.say("Included %d image(s) with the status bar blurred. Look at every image before you post it." % images)
    else:
        app.say("Images were left out. To include them after reviewing them: python adreceipts.py share --include-images")
    app.say("Read the files once more before sharing. Nothing was sent anywhere.")
    return 0
