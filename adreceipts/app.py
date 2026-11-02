"""Shared context for every command: adb access, data folder, runs, catalog."""

from __future__ import annotations

import time

from . import catalog as _catalog
from . import device
from .adb import Adb, SubprocessRunner, find_adb
from .errors import AdReceiptsError
from .store import Runs, data_dir, read_json, require_same_device


class App:
    def __init__(self, args, runner=None, sleep=None, out=None, catalog_dir=None):
        self.args = args
        self._runner = runner
        self.sleep = sleep or time.sleep
        self.out = out or print
        self.catalog_dir = catalog_dir
        self.home = data_dir(getattr(args, "data_dir", None))
        self.runs = Runs(self.home)

    def runner(self):
        if self._runner is None:
            self._runner = SubprocessRunner(find_adb(getattr(self.args, "adb", None)))
        return self._runner

    def adb(self, level="read"):
        return Adb(self.runner(), level)

    def connect(self, level="read"):
        """One authorized, unmanaged phone. Returns adb at the requested level."""
        adb = self.adb("read")
        device.require_one_device(adb)
        device.require_unmanaged(adb)
        return adb.allow(level)

    def catalog(self, props):
        return _catalog.load_for_device(props, self.catalog_dir)

    def run(self):
        return self.runs.resolve(getattr(self.args, "run", None))

    def run_for_device(self, adb, check_build=True):
        """The current run, refusing if it was made on another phone or system build."""
        props, dev = device.identity(adb, self.home)
        run_id, run_dir = self.run()
        saved = (read_json(run_dir / "run.json") or {}).get("device")
        require_same_device(saved, dev, "run %s" % run_id, check_build=check_build)
        return props, dev, run_id, run_dir

    def need(self, run_dir, name, hint):
        data = read_json(run_dir / name)
        if data is None:
            raise AdReceiptsError("%s is missing in this run." % name, hint=hint)
        return data

    def say(self, *lines):
        for line in lines:
            self.out(line)
