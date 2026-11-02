"""Loading and checking the catalog: brand files, protected list, drill rules."""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import schema as _schema
from . import yamlite
from .errors import AdReceiptsError
from .store import REPO_ROOT

PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$")
REPORT_RE = re.compile(r"^(https://\S+|catalog/reports/[A-Za-z0-9_./-]+\.md)$")


def default_dir():
    return REPO_ROOT / "catalog"


class Catalog:
    """All brand files that match one phone, merged for lookups."""

    def __init__(self, files, protected, drill_rules):
        self.files = files
        self.protected_exact, self.protected_prefixes = protected
        self.drill_rules = drill_rules
        self.packages = {}
        self.surfaces = {}
        self.drill_candidates = []
        self.dns_providers = {}
        self.info_checks = []
        for f in files:
            label = "%s/%s" % (f["brand"], f["family"])
            for s in f.get("surfaces", []):
                self.surfaces[s["id"]] = dict(s, catalog=label)
            for p in f.get("packages", []):
                self.packages[p["name"]] = dict(p, catalog=label)
            for d in f.get("drill_candidates", []):
                self.drill_candidates.append(dict(d, catalog=label))
            for d in f.get("dns_providers", []):
                self.dns_providers[d["id"]] = d
            self.info_checks.extend(f.get("info_checks", []))

    @property
    def labels(self):
        return ["%s/%s" % (f["brand"], f["family"]) for f in self.files]

    def system_versions(self):
        out = []
        for f in self.files:
            out.extend(f.get("system_versions", []))
        return out

    def packages_for_surface(self, surface_id):
        names = [n for n, p in self.packages.items() if surface_id in p.get("surfaces", [])]
        s = self.surfaces.get(surface_id, {})
        for n in s.get("turn_off", {}).get("packages", []):
            if n not in names:
                names.append(n)
        return names

    def is_protected(self, name):
        if name in self.protected_exact:
            return True
        return any(name.startswith(prefix) for prefix in self.protected_prefixes)


def load_protected(path):
    exact, prefixes = set(), []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith(".*"):
            prefixes.append(line[:-1])
        else:
            exact.add(line)
    return exact, tuple(prefixes)


def load_schema(catalog_dir):
    return json.loads((Path(catalog_dir) / "schema.json").read_text(encoding="utf-8"))


def catalog_files(catalog_dir):
    root = Path(catalog_dir)
    return sorted(p for p in root.glob("*/*.yml") if p.parent.name != "reports")


def check_file(path, schema_doc, protected=None, repo_root=REPO_ROOT):
    """Return (data, errors) for one catalog file."""
    path = Path(path)
    try:
        data = yamlite.load_file(str(path))
    except yamlite.YamlError as exc:
        return None, [str(exc)]
    errors = _schema.validate(data, schema_doc)
    if errors or not isinstance(data, dict):
        return data, errors
    if path.parent.name != data["brand"] or path.stem != data["family"]:
        errors.append("file must be catalog/%s/%s.yml" % (data["brand"], data["family"]))
    ids = [s["id"] for s in data["surfaces"]]
    if len(ids) != len(set(ids)):
        errors.append("surface ids must be unique")
    names = [p["name"] for p in data["packages"]]
    if len(names) != len(set(names)):
        errors.append("package names must be unique")
    for entry in data["surfaces"] + data["packages"]:
        label = entry.get("id") or entry.get("name")
        if entry.get("proof") == "tested":
            report = entry.get("report", "")
            if not REPORT_RE.match(report):
                errors.append("%s: 'tested' needs a linked report (https URL or catalog/reports/<file>.md)" % label)
            elif report.startswith("catalog/") and not (Path(repo_root) / report).exists():
                errors.append("%s: the linked report %s does not exist" % (label, report))
    for p in data["packages"]:
        for sid in p.get("surfaces", []):
            if sid not in ids:
                errors.append("%s: unknown surface %r" % (p["name"], sid))
        if protected and _protected(p["name"], protected) and p["risk"] != "forbidden":
            errors.append("%s: this package is protected, so its risk must be 'forbidden'" % p["name"])
    for s in data["surfaces"]:
        for n in s["turn_off"].get("packages", []):
            if n not in names:
                errors.append("%s: turn_off package %s must also be listed under packages" % (s["id"], n))
    return data, errors


def _protected(name, protected):
    exact, prefixes = protected
    return name in exact or any(name.startswith(p) for p in prefixes)


def check_all(catalog_dir=None):
    """Validate every catalog file. Returns {path: [errors]}."""
    catalog_dir = Path(catalog_dir or default_dir())
    schema_doc = load_schema(catalog_dir)
    protected = load_protected(catalog_dir / "protected.txt")
    results = {}
    for path in catalog_files(catalog_dir):
        _, errors = check_file(path, schema_doc, protected, repo_root=catalog_dir.parent)
        results[str(path)] = errors
    try:
        yamlite.load_file(str(catalog_dir / "drill_rules.yml"))
    except (yamlite.YamlError, OSError) as exc:
        results[str(catalog_dir / "drill_rules.yml")] = [str(exc)]
    return results


def matches(data, props):
    m = data.get("match", {})
    if m.get("any"):
        return True
    brand = (props.get("ro.product.brand") or "").lower()
    manufacturer = (props.get("ro.product.manufacturer") or "").lower()
    brands = [b.lower() for b in m.get("brands", [])]
    if brand not in brands and manufacturer not in brands:
        return False
    need = m.get("require_prop")
    if need and not props.get(need):
        return False
    return True


def load_for_device(props, catalog_dir=None):
    """Load the catalog files that match this phone. Invalid files stop the run."""
    catalog_dir = Path(catalog_dir or default_dir())
    schema_doc = load_schema(catalog_dir)
    protected = load_protected(catalog_dir / "protected.txt")
    chosen = []
    for path in catalog_files(catalog_dir):
        data, errors = check_file(path, schema_doc, protected, repo_root=catalog_dir.parent)
        if errors:
            raise AdReceiptsError(
                "The catalog file %s is not valid: %s" % (path.name, errors[0]),
                hint="Run: python adreceipts.py catalog-check",
            )
        if matches(data, props):
            chosen.append(data)
    # Generic checks first, then brand files.
    chosen.sort(key=lambda d: (0 if d.get("match", {}).get("any") else 1, d["brand"], d["family"]))
    rules = yamlite.load_file(str(catalog_dir / "drill_rules.yml")) or {}
    return Catalog(chosen, protected, rules)
