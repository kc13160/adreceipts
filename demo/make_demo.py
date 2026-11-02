#!/usr/bin/env python3
"""Build the SIMULATED sample report in demo/sample/.

Everything here comes from tests/fake_adb.py, a fake phone. The screen images
are drawn by this script and say SIMULATED on them. Nothing comes from a real
device. Needs Pillow only to redraw the fake images (pip install Pillow).

    python demo/make_demo.py
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from adreceipts.cli import main  # noqa: E402
from fake_adb import FakeDevice  # noqa: E402

FAKE_SCREENS = ROOT / "demo" / "fake_screens"
SAMPLE = ROOT / "demo" / "sample"

APPS = {
    "com.miui.securitycenter": ("Security (fake)", ["Scan", "Cleaner", "Battery"]),
    "com.android.thememanager": ("Themes (fake)", ["Theme A", "Theme B", "Theme C"]),
}


def font(size):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def draw_screens():
    from PIL import Image, ImageDraw
    FAKE_SCREENS.mkdir(parents=True, exist_ok=True)
    for pkg, (title, rows) in APPS.items():
        for variant in ("ads", "clean"):
            im = Image.new("RGB", (360, 640), (238, 238, 236))
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, 360, 28), fill=(60, 60, 60))
            d.text((10, 6), "12:00   SIMULATED STATUS BAR", fill=(255, 255, 255), font=font(13))
            d.text((20, 50), title, fill=(30, 30, 30), font=font(26))
            y = 110
            for r in rows:
                d.rounded_rectangle((20, y, 340, y + 64), radius=12, fill=(255, 255, 255), outline=(210, 210, 205))
                d.text((36, y + 20), r, fill=(40, 40, 40), font=font(20))
                y += 80
            if variant == "ads":
                d.rounded_rectangle((20, y, 340, y + 110), radius=12, fill=(255, 236, 179), outline=(200, 150, 0), width=3)
                d.text((36, y + 14), "Ad", fill=(160, 90, 0), font=font(22))
                d.text((36, y + 50), "Fake advert for the demo", fill=(80, 60, 0), font=font(18))
            stamp = Image.new("RGBA", (520, 70), (0, 0, 0, 0))
            ImageDraw.Draw(stamp).text((10, 10), "SIMULATED - NOT A REAL PHONE", fill=(200, 30, 30, 170), font=font(30))
            stamp = stamp.rotate(35, expand=True)
            im.paste(stamp, (-60, 200), stamp)
            d.rectangle((0, 600, 360, 640), fill=(200, 30, 30))
            d.text((14, 610), "SIMULATED image (tests/fake_adb.py)", fill=(255, 255, 255), font=font(16))
            im.save(FAKE_SCREENS / ("%s-%s.png" % (pkg, variant)))


def run():
    try:
        draw_screens()
    except ImportError:
        print("Pillow is not installed: reusing the fake images already in demo/fake_screens/.")
    device = FakeDevice()
    device.state["screens_dir"] = str(FAKE_SCREENS)
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "reports"

        def cli(*args):
            rc = main(list(args) + ["--data-dir", str(home)], runner=device, sleep=lambda s: None,
                      out=lambda s="": None)
            if rc != 0:
                raise SystemExit("demo step failed: %s (exit %d)" % (" ".join(args), rc))

        cli("scan", "--screenshots", "--consent")
        cli("backup")
        cli("drill")
        cli("plan", "--select", "pkg:com.miui.msa.global", "pkg:com.miui.analytics",
            "pkg:com.miui.android.fashiongallery", "--approve")
        cli("apply", "--execute")
        cli("verify", "--confirmed", "calls", "sms", "notifications", "payments")
        cli("receipts", "--screenshots", "--consent")
        run_dir = sorted(p for p in home.iterdir() if p.is_dir() and p.name[0].isdigit())[-1]
        if SAMPLE.exists():
            shutil.rmtree(SAMPLE)
        SAMPLE.mkdir(parents=True)
        for name in ("scan.html", "scan.md", "plan.html", "plan.md", "receipts.html", "receipts.md"):
            shutil.copy2(run_dir / name, SAMPLE / name)
        shutil.copytree(run_dir / "screens", SAMPLE / "screens")
        (SAMPLE / "README.md").write_text(
            "# SIMULATED sample\n\n"
            "These files were produced by `python demo/make_demo.py` with the fake phone in `tests/fake_adb.py`.\n"
            "They are **not** results from a real device. The images are drawn by the script and say SIMULATED.\n\n"
            "- [scan.html](scan.html): what the read-only scan shows\n"
            "- [plan.html](plan.html): the plan, with risks and the switches to turn off by hand\n"
            "- [receipts.html](receipts.html): before/after receipts\n",
            encoding="utf-8")
    print("SIMULATED sample written to %s" % SAMPLE)


if __name__ == "__main__":
    run()
