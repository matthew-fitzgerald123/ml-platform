from __future__ import annotations

_TYPE_MAP: dict[str, type] = {"int": int, "float": float, "str": str, "bool": bool}


class FeatureValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_features(features: dict, schema: dict[str, str]) -> None:
    """Raise FeatureValidationError if *features* does not conform to *schema*.

    Schema values are type specs of the form ``"type"`` or ``"type:min:max"``.
    Supported types: int, float, str, bool.
    """
    errors: list[str] = []

    for key, type_spec in schema.items():
        value = features.get(key)

        if value is None:
            errors.append(f"'{key}' is required but missing or null")
            continue

        parts = type_spec.split(":")
        type_name = parts[0]
        expected = _TYPE_MAP.get(type_name)

        if expected is None:
            continue  # unrecognised type — skip rather than block

        if not isinstance(value, expected):
            errors.append(f"'{key}' expected {type_name}, got {type(value).__name__}")
            continue

        if len(parts) == 3 and type_name in ("int", "float"):
            try:
                lo, hi = float(parts[1]), float(parts[2])
                if not (lo <= value <= hi):
                    errors.append(f"'{key}' value {value} out of range [{lo}, {hi}]")
            except ValueError:
                pass

    if errors:
        raise FeatureValidationError(errors)
