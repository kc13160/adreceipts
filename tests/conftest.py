import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from adreceipts.cli import main  # noqa: E402
from fake_adb import FakeDevice  # noqa: E402


class Cli:
    """Runs AdReceipts in-process against a FakeDevice, with no real sleeping."""

    def __init__(self, device, home):
        self.device = device
        self.home = Path(home)
        self.last_output = ""

    def __call__(self, *args):
        lines = []
        rc = main(list(args) + ["--data-dir", str(self.home)], runner=self.device,
                  sleep=lambda s: None, out=lambda s="": lines.append(str(s)))
        self.last_output = "\n".join(lines)
        return rc

    def run_dir(self):
        runs = sorted(p for p in self.home.iterdir() if p.is_dir() and (p / "run.json").exists())
        return runs[-1]

    def read(self, name):
        return json.loads((self.run_dir() / name).read_text(encoding="utf-8"))

    def mark(self):
        """Index into the command log, to look only at commands sent after this point."""
        return len(self.device.log)

    def writes_since(self, mark):
        from fake_adb import is_write
        return [a for a in self.device.log[mark:] if is_write(a)]

    def prepare(self, upto, select=("pkg:com.miui.msa.global", "pkg:com.miui.analytics")):
        steps = ["scan", "backup", "drill", "plan", "approve"]
        for step in steps[: steps.index(upto) + 1]:
            if step == "approve":
                rc = self("plan", "--select", *select, "--approve")
            else:
                rc = self(step)
            assert rc == 0, (step, self.last_output)


@pytest.fixture
def device():
    return FakeDevice()


@pytest.fixture
def cli(device, tmp_path):
    return Cli(device, tmp_path / "reports")
