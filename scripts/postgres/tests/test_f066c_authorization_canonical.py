"""Testes de canonicalizacao JSON F0.66C."""

from hashlib import sha256
import math

import pytest

from f066c_authorization_canonical import (
    canonical_json_bytes,
    canonical_sha256,
)


def test_canonical_output_is_deterministic():
    first = {"z": 2, "a": 1}
    second = {"a": 1, "z": 2}

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert canonical_json_bytes(first) == b'{"a":1,"z":2}'


def test_unicode_is_encoded_as_utf8():
    result = canonical_json_bytes({"reason": "Aprovação explícita"})

    assert result == '{"reason":"Aprovação explícita"}'.encode("utf-8")


def test_nested_objects_are_sorted():
    result = canonical_json_bytes({
        "outer": {"z": 2, "a": 1},
        "items": [3, 2, 1],
    })

    assert result == b'{"items":[3,2,1],"outer":{"a":1,"z":2}}'


@pytest.mark.parametrize(
    "value",
    (
        float("nan"),
        float("inf"),
        float("-inf"),
    ),
)
def test_non_finite_numbers_rejected(value):
    with pytest.raises(ValueError):
        canonical_json_bytes({"value": value})


def test_unsupported_object_rejected():
    with pytest.raises(ValueError):
        canonical_json_bytes({"value": object()})


@pytest.mark.parametrize("value", (None, [], "text", 123))
def test_non_object_root_rejected(value):
    with pytest.raises(TypeError):
        canonical_json_bytes(value)


def test_sha256_matches_canonical_bytes():
    record = {"b": 2, "a": 1}

    expected = sha256(b'{"a":1,"b":2}').hexdigest()

    assert canonical_sha256(record) == expected


def test_sha256_is_independent_of_key_order():
    assert canonical_sha256({"b": 2, "a": 1}) == canonical_sha256({
        "a": 1,
        "b": 2,
    })
