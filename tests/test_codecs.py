import random

import pytest

from stratajanus.index.codecs import (
    MAX_UINT32,
    decode_uints,
    encode_uint,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, b"\x00"),
        (127, b"\x7f"),
        (128, b"\x80\x01"),
        (300, b"\xac\x02"),
        (16383, b"\xff\x7f"),
        (16384, b"\x80\x80\x01"),
    ],
)
def test_known_encodings(value, expected):
    assert encode_uint(value) == expected
    assert decode_uints(expected) == [value]


def test_multiple_values_round_trip():
    values = [0, 1, 127, 128, 300, MAX_UINT32]
    encoded = b"".join(encode_uint(value) for value in values)

    assert decode_uints(encoded) == values


@pytest.mark.parametrize(
    "value, expected",
    [
        (2**14 - 1, b"\xff\x7f"),
        (2**14, b"\x80\x80\x01"),
        (2**21 - 1, b"\xff\xff\x7f"),
        (2**21, b"\x80\x80\x80\x01"),
        (2**28 - 1, b"\xff\xff\xff\x7f"),
        (2**28, b"\x80\x80\x80\x80\x01"),
        (MAX_UINT32, b"\xff\xff\xff\xff\x0f"),
    ],
)
def test_encoding_at_each_uint32_width_boundary(value, expected):
    assert encode_uint(value) == expected
    assert decode_uints(expected) == [value]


def test_decoder_resets_between_values_of_different_widths():
    values = [0, 2**28, 127, 2**14, MAX_UINT32, 1]
    encoded = b"".join(encode_uint(value) for value in values)

    assert decode_uints(encoded) == values


def test_random_values_round_trip():
    random_generator = random.Random(42)

    values = [
        random_generator.randrange(MAX_UINT32 + 1)
        for _ in range(1000)
    ]

    encoded = b"".join(encode_uint(value) for value in values)

    assert decode_uints(encoded) == values


def test_empty_stream():
    assert decode_uints(b"") == []


@pytest.mark.parametrize(
    "value",
    [-1, MAX_UINT32 + 1, True, 1.0, "1", None],
)
def test_invalid_input_is_rejected(value):
    with pytest.raises(ValueError):
        encode_uint(value)


@pytest.mark.parametrize(
    "data",
    [
        b"\x80",                  # Missing final byte.
        b"\x80\x00",              # Redundant encoding of zero.
        b"\x81\x80\x00",          # Redundant high-order zero group.
        b"\xff\xff\xff\xff\x10",  # Exceeds uint32.
        b"\x80\x80\x80\x80\x80",  # Too many continuation bytes.
        b"\x01\x80",              # Valid prefix followed by truncation.
    ],
)
def test_malformed_streams_are_rejected(data):
    with pytest.raises(ValueError):
        decode_uints(data)
