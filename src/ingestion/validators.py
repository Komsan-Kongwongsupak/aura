# src/ingestion/validators.py
import yaml
import numpy as np
import pandas as pd
import pandera as pa
from pandera import Column, DataFrameSchema, Check
from typing import Dict, Any

# helper: map YAML pandas_type -> pandera dtype
PANDAS_TYPE_MAP = {
    "int": int,
    "float": float,
    "object": object,
    "datetime": pa.DateTime,
}


def _make_check_from_constraints(constraints: list):
    """Return a pandera Check (or None) from a constraints list from YAML."""
    checks = []
    if not constraints:
        return None

    for c in constraints:
        name = c.get("name", "").lower()
        expr = c.get("check")
        if name in ("positive",):
            # positive means >= 1 for engine_id, >0 for cycle_number handled elsewhere
            checks.append(Check.ge(1))
        elif name == "non_negative":
            checks.append(Check.ge(0))
        elif name == "finite":
            # ensure finite for floats: allow NaN if nullable; check function returns True for series
            checks.append(
                Check(
                    lambda s: s.dropna().apply(np.isfinite).all(),
                    element_wise=False,
                    error="not all finite"
                )
            )
        elif name == "recent_timestamp" or expr == "is not null":
            checks.append(Check.not_null())
        elif expr:
            # try to parse simple comparisons like "> 0" or ">= 1"
            if isinstance(expr, str):
                expr = expr.strip()
                if expr.startswith(">="):
                    val = float(expr[2:].strip())
                    checks.append(Check.ge(val))
                elif expr.startswith(">"):
                    val = float(expr[1:].strip())
                    checks.append(Check.gt(val))
                elif expr.startswith("<="):
                    val = float(expr[2:].strip())
                    checks.append(Check.le(val))
                elif expr.startswith("<"):
                    val = float(expr[1:].strip())
                    checks.append(Check.lt(val))
                # otherwise ignore complex expressions
    if checks:
        # combine checks into a single Check using lambda applying each
        def combined(series):
            for ck in checks:
                # use ck.pandas_check to evaluate? Simpler: run each check functionally
                # here we simply use the first check's callable for erroring; pandera will apply each separately
                pass
        # return a list to handle applying multiple checks via Column(checks=[...])
        return checks
    return None


def build_pandera_schema_from_yaml(yaml_path: str) -> DataFrameSchema:
    """Load YAML schema and build a pandera DataFrameSchema."""
    with open(yaml_path, "r") as f:
        schema_yaml = yaml.safe_load(f)

    columns = schema_yaml.get("columns", [])
    column_map: Dict[str, Column] = {}

    for col in columns:
        name = col["name"]
        pandas_type = col.get("pandas_type", "object")
        nullable = col.get("nullable", True)
        constraints = col.get("constraints", []) or []

        # map to pandera dtype or class
        dtype = PANDAS_TYPE_MAP.get(pandas_type, object)

        # create checks list
        checks = _make_check_from_constraints(constraints)
        if checks is None:
            # no checks
            column_map[name] = Column(dtype, nullable=nullable)
        else:
            # checks might be a list; pass as checks parameter
            column_map[name] = Column(dtype, nullable=nullable, checks=checks)

    return DataFrameSchema(column_map, coerce=True)


def validate_dataframe_from_yaml(df: pd.DataFrame, yaml_path: str) -> pd.DataFrame:
    """
    Coerce types and run pandera validation based on YAML schema.
    Returns validated DataFrame or raises pandera.errors.SchemaError.
    """
    schema = build_pandera_schema_from_yaml(yaml_path)

    # Some pre-coercions: parse datetime-like columns if present in schema
    for col_def in schema.columns:
        # if pandas_type == datetime we want to parse strings
        # We check original yaml: simpler is to attempt parse if dtype is pa.DateTime
        pass

    # Use pandera's validate (coerce=True in schema will try to cast types)
    validated_df = schema.validate(df, lazy=True)

    return validated_df
