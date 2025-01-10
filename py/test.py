# todo: use pytest?

from pack import (
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


def test(value, T=None):
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


def main():
    test(5, T=uint32_type)

    test([-1, 1, -2, 2, -3, 3, -4, 5], T=list_type.of(int8_type))

    test("hello world")

    test(Nullopt, T=optional_type.of(uint32_type))

    test(
        ([-1, -2, 3, 4], Nullopt, "hi", 12),
        T=tuple_type.of(
            list_type.of(int8_type),
            optional_type.of(bool_type),
            string_type,
            uint32_type,
        ),
    )


if __name__ == "__main__":
    main()
