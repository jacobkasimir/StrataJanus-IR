"""Unsigned 32-bit variable-byte integer encoding.

The format uses unsigned LEB128:
- seven payload bits per byte;
- least-significant groups first;
- high bit set when another byte follows.
"""

MAX_UINT32 = (1 << 32) - 1


def encode_uint(value: int) -> bytes:
    """Encode one unsigned 32-bit integer.

    Args:
        value: Integer between zero and 2**32 - 1.

    Returns:
        The canonical variable-byte representation.

    Raises:
        ValueError: If the input is outside the supported range.
    """
    if type(value) is not int or not 0 <= value <= MAX_UINT32:
        raise ValueError("Value must be an unsigned 32-bit integer.")

    output = bytearray()

    while value >= 128:
        output.append((value & 0x7F) | 0x80)
        value >>= 7

    output.append(value)

    return bytes(output)


def decode_uints(data: bytes) -> list[int]:
    """Decode a stream of unsigned 32-bit integers.

    Raises:
        ValueError: If the stream contains truncated, overflowing,
            or noncanonical encodings.
    """
    values = []
    value = 0
    shift = 0

    for byte in data:
        payload = byte & 0x7F
        value |= payload << shift

        if value > MAX_UINT32:
            raise ValueError("Encoded integer exceeds uint32 range.")

        if byte & 0x80:
            shift += 7

            if shift >= 35:
                raise ValueError("Encoded integer is too long.")

            continue

        # A multi-byte representation must not end with a zero
        # high-order group; that would encode the value redundantly.
        if shift > 0 and payload == 0:
            raise ValueError("Noncanonical integer encoding.")

        values.append(value)
        value = 0
        shift = 0

    if shift != 0:
        raise ValueError("Truncated variable-byte integer.")

    return values