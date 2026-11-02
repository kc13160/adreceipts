"""catalog-check: validate every catalog file against catalog/schema.json and the rules."""

from __future__ import annotations

from pathlib import Path

from . import catalog


def run(app):
    results = catalog.check_all(app.catalog_dir)
    bad = 0
    for path, errors in sorted(results.items()):
        name = Path(path).as_posix().split("/catalog/")[-1]
        if errors:
            bad += 1
            app.say("[INVALID] %s" % name)
            for e in errors:
                app.say("    %s" % e)
        else:
            app.say("[OK] %s" % name)
    return 1 if bad else 0
