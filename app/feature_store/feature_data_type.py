from enum import StrEnum


class FeatureDataType(StrEnum):
    """
    Supported feature value types.
    """

    DECIMAL = "DECIMAL"

    INTEGER = "INTEGER"

    BOOLEAN = "BOOLEAN"

    STRING = "STRING"