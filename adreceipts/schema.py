"""A small JSON Schema checker for catalog/schema.json (standard library only).

Supports the keywords the catalog schema uses: type, properties, required,
additionalProperties (boolean), items, enum, const, pattern, minLength,
maxLength, minItems, uniqueItems, $ref to #/definitions/..., allOf, if/then.
The test suite also checks the catalog with the `jsonschema` package when it
is installed, so both readings agree.
"""

from __future__ import annotations

import re

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _is_type(value, name):
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[name])


def validate(instance, schema, root=None, path="$"):
    """Return a list of error strings (empty when valid)."""
    root = root if root is not None else schema
    errors = []

    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/definitions/"):
            return ["%s: unsupported $ref %s" % (path, ref)]
        target = root["definitions"][ref.split("/")[-1]]
        return validate(instance, target, root, path)

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(instance, t) for t in types):
            return ["%s: expected %s" % (path, " or ".join(types))]

    if "const" in schema and instance != schema["const"]:
        errors.append("%s: must be %r" % (path, schema["const"]))
    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: %r is not one of %s" % (path, instance, ", ".join(map(str, schema["enum"]))))

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append("%s: too short" % path)
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append("%s: too long" % path)
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append("%s: %r does not match %s" % (path, instance, schema["pattern"]))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append("%s: needs at least %d item(s)" % (path, schema["minItems"]))
        if schema.get("uniqueItems"):
            seen = []
            for item in instance:
                if item in seen:
                    errors.append("%s: duplicate item %r" % (path, item))
                seen.append(item)
        if "items" in schema:
            for n, item in enumerate(instance):
                errors.extend(validate(item, schema["items"], root, "%s[%d]" % (path, n)))

    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append("%s: missing required field %r" % (path, key))
        for key, value in instance.items():
            if key in props:
                errors.extend(validate(value, props[key], root, "%s.%s" % (path, key)))
            elif schema.get("additionalProperties") is False:
                errors.append("%s: unknown field %r" % (path, key))

    for sub in schema.get("allOf", []):
        errors.extend(validate(instance, sub, root, path))

    if "if" in schema:
        if not validate(instance, schema["if"], root, path):
            if "then" in schema:
                errors.extend(validate(instance, schema["then"], root, path))
        elif "else" in schema:
            errors.extend(validate(instance, schema["else"], root, path))

    return errors
