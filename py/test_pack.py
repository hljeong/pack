from py_utils.test import Parameters, parametrize

from pack.pack import (
    Nullopt,
    resolve_type,
    pack_one,
    unpack_one,
    UInt32,
    Int8,
    Bool,
    List,
    String,
    Optional,
    Tuple,
)

parameters = [
    Parameters("UInt32", 5, UInt32),
    Parameters("List[Int8]", [-1, 1, -2, 2, -3, 3, -4, 5], List[Int8]),
    Parameters("String", "hello world", None),
    Parameters("Optional[UInt32] = Nullopt", Nullopt, Optional[UInt32]),
    Parameters(
        "Tuple",
        ([-1, -2, 3, 4], Nullopt, "hi", 12),
        Tuple[List[Int8], Optional[Bool], String, UInt32],
    ),
]


@parametrize("value, T", parameters)
def test_pack(value, T):
    T = T or resolve_type(value)

    print(f"input: {value!r}")

    packed = pack_one[T](value)
    print("packed:")
    packed.dump()

    try:
        unpacked = unpack_one[T](packed)
        print(f"unpacked: {value!r}")
        assert value == unpacked
    except Exception as e:
        print(f"failed to unpack: {e}")
        assert False, f"failed to unpack: {e}"
