"""Each catalog file validates, and 'tested' needs a linked report."""

import json
import shutil
from pathlib import Path

import pytest

from adreceipts import catalog, yamlite
from adreceipts import schema as mini_schema

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
FILES = catalog.catalog_files(CATALOG)


def test_there_are_catalog_files():
    names = {p.relative_to(CATALOG).as_posix() for p in FILES}
    assert {"xiaomi/hyperos.yml", "generic/android.yml"} <= names


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.relative_to(CATALOG).as_posix())
def test_catalog_file_is_valid(path):
    schema_doc = catalog.load_schema(CATALOG)
    protected = catalog.load_protected(CATALOG / "protected.txt")
    data, errors = catalog.check_file(path, schema_doc, protected, repo_root=ROOT)
    assert errors == []


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.relative_to(CATALOG).as_posix())
def test_reader_matches_pyyaml_and_jsonschema(path):
    yaml = pytest.importorskip("yaml")
    jsonschema = pytest.importorskip("jsonschema")
    ours = yamlite.load_file(str(path))
    theirs = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert ours == theirs
    jsonschema.validate(theirs, catalog.load_schema(CATALOG))


def test_all_entries_start_documented():
    for path in FILES:
        data = yamlite.load_file(str(path))
        for entry in data["surfaces"] + data["packages"]:
            assert entry["proof"] == "documented", (path, entry.get("id") or entry.get("name"))
            assert entry["source"].startswith("https://")


def test_catalog_check_command(cli):
    assert cli("catalog-check") == 0
    assert "[OK] xiaomi/hyperos.yml" in cli.last_output


def _copy_catalog(tmp_path):
    dst = tmp_path / "catalog"
    shutil.copytree(CATALOG, dst)
    return dst


def _edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_tested_without_report_fails(tmp_path):
    dst = _copy_catalog(tmp_path)
    f = dst / "xiaomi" / "hyperos.yml"
    _edit(f, 'proof: "documented"\n    surfaces: ["msa_system_ads"]', 'proof: "tested"\n    surfaces: ["msa_system_ads"]')
    results = catalog.check_all(dst)
    errors = results[str(f)]
    assert any("report" in e for e in errors)


def test_tested_with_missing_report_file_fails(tmp_path):
    dst = _copy_catalog(tmp_path)
    f = dst / "xiaomi" / "hyperos.yml"
    _edit(f, 'proof: "documented"\n    surfaces: ["msa_system_ads"]',
          'proof: "tested"\n    report: "catalog/reports/nope.md"\n    surfaces: ["msa_system_ads"]')
    errors = catalog.check_all(dst)[str(f)]
    assert any("does not exist" in e for e in errors)


def test_tested_with_report_passes(tmp_path):
    dst = _copy_catalog(tmp_path)
    (dst / "reports" / "xiaomi-example.md").write_text("# report\n", encoding="utf-8")
    f = dst / "xiaomi" / "hyperos.yml"
    _edit(f, 'proof: "documented"\n    surfaces: ["msa_system_ads"]',
          'proof: "tested"\n    report: "catalog/reports/xiaomi-example.md"\n    surfaces: ["msa_system_ads"]')
    assert catalog.check_all(dst)[str(f)] == []


def test_protected_package_must_be_forbidden(tmp_path):
    dst = _copy_catalog(tmp_path)
    f = dst / "xiaomi" / "hyperos.yml"
    _edit(f, 'role: "Security app (hosts phone protections)"\n    category: "ads"\n    risk: "forbidden"',
          'role: "Security app (hosts phone protections)"\n    category: "ads"\n    risk: "safe"')
    errors = catalog.check_all(dst)[str(f)]
    assert any("protected" in e for e in errors)


def test_invalid_catalog_stops_commands(tmp_path, device):
    dst = _copy_catalog(tmp_path)
    _edit(dst / "xiaomi" / "hyperos.yml", 'risk: "prudent"', 'risk: "maybe"')
    from adreceipts.cli import main
    lines = []
    rc = main(["scan", "--data-dir", str(tmp_path / "r")], runner=device, sleep=lambda s: None,
              out=lines.append, catalog_dir=dst)
    assert rc == 1
    assert "not valid" in "\n".join(lines)


@pytest.mark.parametrize("text", [
    "a: yes", "a: 1.5", "a:\n\tb: 1", "a: 'x", "a: b: c", "a: 1\na: 2", "a: &anchor x", "a: |\n  block",
])
def test_yaml_reader_refuses_ambiguous_input(text):
    with pytest.raises(yamlite.YamlError):
        yamlite.loads(text)


def test_yaml_reader_basics():
    doc = yamlite.loads('# c\na: "x # not comment"\nb: [1, "two", three]\nc:\n  - d: 1\n    e: true\n  - plain text\nf: {}\ng: null\n')
    assert doc == {"a": "x # not comment", "b": [1, "two", "three"], "c": [{"d": 1, "e": True}, "plain text"], "f": {}, "g": None}


def test_mini_schema_matches_rules():
    schema_doc = catalog.load_schema(CATALOG)
    data = yamlite.load_file(str(CATALOG / "generic" / "android.yml"))
    assert mini_schema.validate(data, schema_doc) == []
    bad = json.loads(json.dumps(data))
    bad["surfaces"][0]["proof"] = "tested"
    assert any("report" in e for e in mini_schema.validate(bad, schema_doc))
    bad["surfaces"][0]["unexpected"] = 1
    assert any("unknown field" in e for e in mini_schema.validate(bad, schema_doc))
