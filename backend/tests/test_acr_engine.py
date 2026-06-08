from __future__ import annotations

import pytest
from app.core.acr_engine import build_operator_sql


# Use build_operator_sql directly — it's the core query-building function


def test_build_operator_sql_eq():
    cond, params = build_operator_sql("field1", "eq", "value1", 1)
    assert cond == "field1 = $1"
    assert params == ["value1"]


def test_build_operator_sql_ne():
    cond, params = build_operator_sql("field1", "ne", "value1", 1)
    assert cond == "field1 != $1"


def test_build_operator_sql_in():
    cond, params = build_operator_sql("field1", "in", ["a", "b", "c"], 1)
    assert "field1 IN ($1, $2, $3)" == cond
    assert params == ["a", "b", "c"]


def test_build_operator_sql_not_in():
    cond, params = build_operator_sql("field1", "not_in", ["x", "y"], 1)
    assert cond == "field1 NOT IN ($1, $2)"
    assert params == ["x", "y"]


def test_build_operator_sql_intersects():
    cond, params = build_operator_sql("tags", "intersects", ["tag1", "tag2"], 1)
    assert "&&" in cond
    assert params == ["tag1", "tag2"]


def test_build_operator_sql_contains():
    cond, params = build_operator_sql("roles", "contains", "admin", 1)
    assert cond == "$1 = ANY(roles)"


def test_build_operator_sql_gt():
    cond, params = build_operator_sql("age", "gt", 18, 1)
    assert cond == "age > $1"


def test_build_operator_sql_gte():
    cond, params = build_operator_sql("age", "gte", 18, 1)
    assert cond == "age >= $1"


def test_build_operator_sql_lt():
    cond, params = build_operator_sql("age", "lt", 100, 1)
    assert cond == "age < $1"


def test_build_operator_sql_lte():
    cond, params = build_operator_sql("age", "lte", 100, 1)
    assert cond == "age <= $1"


def test_build_operator_sql_unknown_returns_true():
    cond, params = build_operator_sql("x", "nonexistent", "v", 1)
    assert cond == "TRUE"
    assert params == []


def test_build_operator_sql_in_empty_list():
    cond, params = build_operator_sql("f", "in", [], 1)
    assert cond == "FALSE"


