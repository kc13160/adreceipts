"""Docs make no claim of working on every phone, no fixed gains, no "guaranteed" or "100%" safety claims."""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN = [
    (r"\bguarantee", "no guarantee claims"),
    (r"\b100\s*%", "no 100% claims"),
    (r"\b(works?|working|runs?|tested) on (every|all|any)\b", "no claim of working on every phone"),
    (r"\b(every|all|any) android (phone|device)s?\b", "no claim of covering every phone"),
    (r"\b\d+\s*%\s*(faster|less|more|fewer|better|of (the )?ads)", "no fixed gains"),
    (r"\b(boosts?|improves?|extends?|saves?|frees?) (your |the )?(battery|ram|memory|performance|speed)", "no gains"),
    (r"\bmakes? (your |the )?phone (faster|quicker)", "no speed claims"),
    (r"\b(has been|was|were|is) tested on (my|our|the owner|a real)", "no claim of real-device testing"),
    (r"\bremoves? (all|every) ads?\b", "no ad-free promise"),
]


def doc_files():
    try:
        out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md", "*.yml", "*.html"], cwd=str(ROOT), stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=30).stdout.decode()
        files = [ROOT / f for f in out.splitlines() if f]
    except (OSError, subprocess.SubprocessError):
        files = []
    if not files:
        files = [p for p in ROOT.rglob("*") if p.suffix in (".md", ".yml", ".html")
                 and ".venv" not in p.parts and "reports" not in p.parts and p.name != "BUILD.md"]
    return [f for f in files if f.exists() and f.name != "BUILD.md"]


NEGATION = re.compile(r"(\bnot|\bno|\bnothing|\bnone|\bnever|\bunless|\bwithout|\buntil|n't|\bcannot)\b[^.!?\n]*$", re.I)


def claims(text):
    """Forbidden phrases that are not part of a negated sentence ("not yet tested on a real device")."""
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    found = []
    for pattern, why in FORBIDDEN:
        for m in re.finditer(pattern, text, re.I):
            before = text[max(0, m.start() - 80):m.start()]
            if NEGATION.search(before):
                continue
            found.append("%r (%s)" % (m.group(0), why))
    return found


@pytest.mark.parametrize("path", doc_files(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_no_forbidden_claims(path):
    assert claims(path.read_text(encoding="utf-8")) == []


def test_claim_checker_catches_claims():
    assert claims("AdReceipts works on every phone.")
    assert claims("It is 100% safe.")
    assert claims("Guaranteed to remove ads.")
    assert claims("Your phone gets 30% faster.")
    assert claims("This was tested on my phone.")
    assert claims("It boosts battery life.")
    assert not claims("Not yet tested on a real device.")
    assert not claims("Docs must not claim it works on every phone.")
    assert not claims("<style>img { width: 100%; }</style>")


def test_readme_has_status_banner_and_wording():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Experimental. Not yet tested on a real device. Use at your own risk and back up your data first." in text
    assert "Designed for Android. Tested only on the models listed in the catalog." in text
    assert "SIMULATED" in text


def test_demo_sample_is_labelled_simulated():
    sample = ROOT / "demo" / "sample"
    pages = list(sample.glob("*.html"))
    assert pages
    for page in pages:
        assert "SIMULATED" in page.read_text(encoding="utf-8"), page.name


def test_required_files_exist():
    for name in ["README.md", "PROMPT.md", "CLAUDE.md", "AGENTS.md", "CONTRIBUTING.md", "SECURITY.md", "PRIVACY.md",
                 "NOTICE.md", "LICENSE", "CHANGELOG.md", "DECISIONS.md", "REPORT.md", "TEST_ON_PHONE.md", "LAUNCH.md",
                 "adreceipts.py", "catalog/protected.txt", "catalog/drill_rules.yml", "catalog/schema.json",
                 "catalog/xiaomi/hyperos.yml", "catalog/generic/android.yml", "templates/report.html",
                 "templates/receipts.html", "docs/how-it-works.md", "docs/restore-and-recovery.md", "docs/faq.md",
                 "tests/fake_adb.py", ".github/workflows/tests.yml", ".github/ISSUE_TEMPLATE/ad_surface.yml",
                 ".github/ISSUE_TEMPLATE/device_report.yml", ".gitignore"]:
        p = ROOT / name
        assert p.exists() and p.stat().st_size > 100, name


def test_templates_load_nothing_external():
    for t in (ROOT / "templates").glob("*.html"):
        text = t.read_text(encoding="utf-8")
        assert "<script" not in text
        assert "http://" not in text and "https://" not in text
        assert "@import" not in text
