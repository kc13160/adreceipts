"""Command line: python adreceipts.py <command> [options]."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .app import App
from .errors import AdReceiptsError

COMMANDS = {
    "doctor": "Check adb, authorization, one device, and work profiles. Changes nothing.",
    "scan": "Find ad sources on the phone. Read-only: changes nothing.",
    "backup": "Save the current state and write a standalone restore script.",
    "drill": "Prove undo works on this phone with one harmless package.",
    "plan": "Show what can be turned off, with risks. Select items and approve.",
    "apply": "Apply the approved plan. Dry run unless --execute.",
    "verify": "Health checks plus a checklist: calls, SMS, notifications, payment apps.",
    "receipts": "Build the before/after proof page.",
    "restore": "Undo changes recorded in the journal (--batch ID or --all).",
    "recheck": "After an update: show what came back or changed. Read-only.",
    "share": "Make a sanitized copy of the reports, without images by default.",
    "catalog-check": "Validate the catalog files.",
}


def build_parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--adb", metavar="PATH", help="path to adb (default: ADRECEIPTS_ADB, then adb on PATH)")
    common.add_argument("--data-dir", metavar="DIR", help="where reports are kept (default: ADRECEIPTS_HOME or ./reports)")
    common.add_argument("--run", metavar="ID", help="use this run instead of the latest one")

    parser = argparse.ArgumentParser(
        prog="adreceipts",
        description="Find the ads built into an Android phone, remove them with approval, and show before/after proof. "
                    "No root. Every change can be undone.",
    )
    parser.add_argument("--version", action="version", version="AdReceipts %s" % __version__)
    sub = parser.add_subparsers(dest="command", metavar="command")

    for name, help_text in COMMANDS.items():
        p = sub.add_parser(name, parents=[common], help=help_text, description=help_text)
        if name in ("scan", "receipts"):
            p.add_argument("--screenshots", action="store_true", help="also collect screen evidence (off by default)")
            p.add_argument("--consent", action="store_true", help="confirm you read and accept the screenshot notice")
        if name == "plan":
            p.add_argument("--select", nargs="+", default=[], metavar="ID", help="select items by ID")
            p.add_argument("--deselect", nargs="+", default=[], metavar="ID", help="remove items by ID")
            p.add_argument("--dns", metavar="PROVIDER", help="add Private DNS filtering: a provider id from the list, or 'custom'")
            p.add_argument("--dns-host", metavar="HOST", help="hostname for --dns custom")
            p.add_argument("--no-dns", action="store_true", help="remove the DNS choice from the plan")
            p.add_argument("--approve", action="store_true", help="approve the selected items")
        if name == "apply":
            p.add_argument("--execute", action="store_true", help="really change the phone (otherwise: dry run)")
            p.add_argument("--method", choices=["disable", "uninstall"], default="disable",
                           help="disable (default, pm disable-user) or uninstall for user 0 (advanced)")
            p.add_argument("--i-understand-uninstall", action="store_true",
                           help="required with --method uninstall")
        if name == "verify":
            p.add_argument("--confirmed", nargs="+", default=[], metavar="CHECK",
                           choices=["calls", "sms", "notifications", "payments"],
                           help="checks you did by hand and that work")
            p.add_argument("--problem", metavar="TEXT", help="describe something that stopped working")
        if name == "restore":
            g = p.add_mutually_exclusive_group()
            g.add_argument("--batch", metavar="ID", help="undo one batch")
            g.add_argument("--all", action="store_true", help="undo every change recorded in this run")
        if name == "share":
            p.add_argument("--include-images", action="store_true",
                           help="include screenshots, after you reviewed them (needs Pillow for blurring)")
    return parser


def _dispatch(name):
    from . import apply, backup, catalog_check, doctor, drill, plan, recheck, receipts, restore, scan, share, verify
    return {
        "doctor": doctor.run, "scan": scan.run, "backup": backup.run, "drill": drill.run,
        "plan": plan.run, "apply": apply.run, "verify": verify.run, "receipts": receipts.run,
        "restore": restore.run, "recheck": recheck.run, "share": share.run,
        "catalog-check": catalog_check.run,
    }[name]


def main(argv=None, runner=None, sleep=None, out=None, catalog_dir=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    app = App(args, runner=runner, sleep=sleep, out=out, catalog_dir=catalog_dir)
    try:
        return int(_dispatch(args.command)(app) or 0)
    except AdReceiptsError as exc:
        app.out("Error: %s" % exc.message)
        if exc.hint:
            app.out("What to do: %s" % exc.hint)
        return exc.exit_code
    except KeyboardInterrupt:
        app.out("Stopped by the user. If a change was in progress, run: python adreceipts.py restore --all")
        return 130
