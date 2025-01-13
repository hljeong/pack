from py_utils.test import Parameters, parametrize

from pack.pack import (
    Nullopt,
    resolve_type,
    pack_one,
    unpack_one,
    UInt32Type,
    Int8Type,
    BoolType,
    ListType,
    StringType,
    OptionalType,
    TupleType,
)

parameters = [
    Parameters("uint32", 5, UInt32Type),
    Parameters("list[int8]", [-1, 1, -2, 2, -3, 3, -4, 5], ListType.of(Int8Type)),
    Parameters("string", "hello world", None),
    Parameters("optional[uint32] = Nullopt", Nullopt, OptionalType.of(UInt32Type)),
    Parameters(
        "tuple",
        ([-1, -2, 3, 4], Nullopt, "hi", 12),
        TupleType.of(
            ListType.of(Int8Type),
            OptionalType.of(BoolType),
            StringType,
            UInt32Type,
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

    try:
        unpacked = unpack_one(T, packed)
        print(f"unpacked: {value!r}")
        assert value == unpacked
    except Exception as e:
        print(f"failed to unpack: {e}")
        assert False, f"failed to unpack: {e}"
