from py_utils.test import Parameters, parametrize

from pack.pack import (
    Nullopt,
    resolve_type,
    pack_one,
    unpack_one,
    uint32_type,
    int8_type,
    bool_type,
    list_type,
    string_type,
    optional_type,
    tuple_type,
)

parameters = [
    Parameters("uint32", 5, uint32_type),
    Parameters("list[int8]", [-1, 1, -2, 2, -3, 3, -4, 5], list_type.of(int8_type)),
    Parameters("string", "hello world", None),
    Parameters("optional[uint32] = Nullopt", Nullopt, optional_type.of(uint32_type)),
    Parameters(
        "tuple",
        ([-1, -2, 3, 4], Nullopt, "hi", 12),
        tuple_type.of(
            list_type.of(int8_type),
            optional_type.of(bool_type),
            string_type,
            uint32_type,
        ),
    ),
]


@parametrize("value, T", parameters)
def test_pack(value, T):
    T = T or resolve_type(value)

    print(f"input: {value!r}")

    packed = pack_one(value, T=T)
    print("packed:")
    packed.dump()

    unpacked = unpack_one(T, packed)
    if unpacked is None:
        print("failed to unpack")
    else:
        print(f"unpacked: {value!r}")

    assert value == unpacked
