from py_utils.test import Parameters, parametrize

from pack.pack import (
    Nullopt,
    deduce_type,
    pack_one,
    unpack_one,
    UInt8,
    UInt32,
    Int8,
    List,
    Optional,
    Tuple,
)

parameters = [
    Parameters("UInt32", 5),
    Parameters("List[Int8]", List[Int8]([-1, 1, -2, 2, -3, 3, -4, 5])),
    Parameters("String", "hello world"),
    Parameters("Optional[UInt32] = Nullopt", Optional[UInt32](Nullopt)),
    Parameters("Tuple", ([-1, -2, 3, 4], False, "hi", 12)),
]


@parametrize("value", parameters)
def test_pack(value):
    T = deduce_type(value)
    print(f"input: {value!r}")

    packed = pack_one(value)
    print("packed:")
    packed.dump()

    try:
        unpacked = unpack_one[T](packed)
        print(f"unpacked: {value!r}")
        assert value == unpacked
    except Exception as e:
        print(f"failed to unpack: {e}")
        assert False, f"failed to unpack: {e}"


def test_pack_misc():
    assert str(List) == "List"
    todo: fix
    assert repr(Tuple[Optional[UInt8]]) == "type Tuple[Optional[UInt8]]"
