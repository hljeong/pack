from enum import Enum
import struct

# todo: type annotations?
# todo: unpack<T>() and unpack<(T1, T2)>() syntax?


class type_id(Enum):
    type_type = 0x01
    uint8_type = 0x10
    uint16_type = 0x11
    uint32_type = 0x12
    uint64_type = 0x13
    int8_type = 0x18
    int16_type = 0x19
    int32_type = 0x1A
    int64_type = 0x1B
    float_type = 0x20
    double_type = 0x21
    bool_type = 0x30
    list_type = 0x40
    string_type = 0x41


def resolve_type(value):
    def fail(reason=None):
        if reason:
            raise NotImplementedError(f"{value!r} has unsupported type: {reason}")
        else:
            raise NotImplementedError(f"{value!r} has unsupported type")

    if isinstance(value, int):
        return int32_type

    elif isinstance(value, bool):
        return bool_type

    elif isinstance(value, list):
        if len(value) == 0:
            fail("list with lenght 0")

        elem_type = resolve_type(value[0])
        # todo: implement any(not castable(elem, elem_type) for ...)?
        if any(resolve_type(elem) is not elem_type for elem in value):
            fail("not all elements have the same type")

        return list_type.of(elem_type)

    elif isinstance(value, str):
        return string_type

    fail("not implemented")


class Pack:
    def __init__(self, *comps):
        self.data = bytes()
        for comp in comps:
            if isinstance(comp, Pack):
                self.data += comp.data
            elif isinstance(comp, bytes):
                self.data += comp
            else:
                self.data += bytes((comp,))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return self.data[idx]

    def __add__(self, other):
        return Pack(self, other)

    def __eq__(self, other):
        return self.data == Pack(other).data

    def dump(self):
        i = 0
        for byte in self.data:
            if i:
                print("\n "[(i % 8 + 7) // 8], end="")
            i += 1
            print(f"{byte:02x}", end="")
        print()


class Packer:
    def __init__(self):
        self.data = Pack()

    def _push(self, data):
        self.data += data

    def pack_value(self, value, T=None):
        T = T or resolve_type(value)
        assert T is not None
        self._push(T.pack(value))
        return self

    def pack(self, value, T=None):
        T = T or resolve_type(value)
        assert T is not None
        self._push(T.type_info)
        self.pack_value(value, T=T)
        return self


class Unpacker:
    def __init__(self, data):
        self.data = Pack(data)
        self.idx = 0

    def consume(self, n):
        if self.idx + n > len(self.data):
            return None
        data = self.data[self.idx : self.idx + n]
        self.idx += n
        return data

    def _expect(self, expected):
        data = self.consume(len(expected))
        return data == expected

    def unpack_value(self, T):
        return T.unpack(self)

    def unpack(self, T):
        return self.unpack_value(T) if self._expect(T.type_info) else None


# todo: reduce boilerplate
class uint8_type:
    type_info = Pack(type_id.uint8_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert 0 <= value < (1 << 8)

    @staticmethod
    def pack(value):
        uint8_type.validate(value)
        return Pack(struct.pack("<B", value))

    @staticmethod
    def unpack(up):
        data = up.consume(1)
        return None if data is None else struct.unpack("<B", data)[0]


class uint16_type:
    type_info = Pack(type_id.uint16_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert 0 <= value < (1 << 16)

    @staticmethod
    def pack(value):
        uint16_type.validate(value)
        return Pack(struct.pack("<H", value))

    @staticmethod
    def unpack(up):
        data = up.consume(2)
        return None if data is None else struct.unpack("<H", data)[0]


class uint32_type:
    type_info = Pack(type_id.uint32_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert 0 <= value < (1 << 32)

    @staticmethod
    def pack(value):
        uint32_type.validate(value)
        return Pack(struct.pack("<I", value))

    @staticmethod
    def unpack(up):
        data = up.consume(4)
        return None if data is None else struct.unpack("<I", data)[0]


class uint64_type:
    type_info = Pack(type_id.uint64_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert 0 <= value < (1 << 64)

    @staticmethod
    def pack(value):
        uint64_type.validate(value)
        return Pack(struct.pack("<Q", value))

    @staticmethod
    def unpack(up):
        data = up.consume(8)
        return None if data is None else struct.unpack("<Q", data)[0]


class int8_type:
    type_info = Pack(type_id.int8_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert -(1 << 7) <= value < (1 << 7)

    @staticmethod
    def pack(value):
        int8_type.validate(value)
        return Pack(struct.pack("<b", value))

    @staticmethod
    def unpack(up):
        data = up.consume(1)
        return None if data is None else struct.unpack("<b", data)[0]


class int16_type:
    type_info = Pack(type_id.int16_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert -(1 << 15) <= value < (1 << 15)

    @staticmethod
    def pack(value):
        int16_type.validate(value)
        return Pack(struct.pack("<h", value))

    @staticmethod
    def unpack(up):
        data = up.consume(2)
        return None if data is None else struct.unpack("<h", data)[0]


class int32_type:
    type_info = Pack(type_id.int32_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert -(1 << 31) <= value < (1 << 31)

    @staticmethod
    def pack(value):
        int32_type.validate(value)
        return Pack(struct.pack("<i", value))

    @staticmethod
    def unpack(up):
        data = up.consume(4)
        return None if data is None else struct.unpack("<i", data)[0]


class int64_type:
    type_info = Pack(type_id.int64_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert -(1 << 63) <= value < (1 << 63)

    @staticmethod
    def pack(value):
        int64_type.validate(value)
        return Pack(struct.pack("<q", value))

    @staticmethod
    def unpack(up):
        data = up.consume(8)
        return None if data is None else struct.unpack("<q", data)[0]


class float_type:
    type_info = Pack(type_id.float_type.value)

    # todo: possible to automate checking for castable types?
    @staticmethod
    def validate(value):
        assert isinstance(value, float) or isinstance(value, int)

    @staticmethod
    def pack(value):
        float_type.validate(value)
        return Pack(struct.pack("<f", value))

    @staticmethod
    def unpack(up):
        data = up.consume(4)
        return None if data is None else struct.unpack("<f", data)[0]


class double_type:
    type_info = Pack(type_id.double_type.value)

    # todo: possible to automate checking for castable types?
    @staticmethod
    def validate(value):
        assert isinstance(value, float) or isinstance(value, int)

    @staticmethod
    def pack(value):
        double_type.validate(value)
        return Pack(struct.pack("<d", value))

    @staticmethod
    def unpack(up):
        data = up.consume(8)
        return None if data is None else struct.unpack("<d", data)[0]


class bool_type:
    type_info = Pack(type_id.bool_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, bool)

    @staticmethod
    def pack(value):
        bool_type.validate(value)
        return Pack(1 if value else 0)

    @staticmethod
    def unpack(up):
        data = up.consume(1)
        return None if data is None else bool(data[0])


class list_type:
    _cache = dict()

    # todo: __getitem__ would be nice
    # todo: maybe even <T> syntax
    @staticmethod
    def of(elem_type):
        if elem_type not in list_type._cache:

            class list_type_inst:
                type_info = Pack(type_id.list_type.value, elem_type.type_info)

                @staticmethod
                def validate(value):
                    assert isinstance(value, list)
                    for elem in value:
                        elem_type.validate(elem)

                @staticmethod
                def pack(value):
                    list_type_inst.validate(value)
                    p = Packer()
                    p.pack_value(len(value), T=uint32_type)
                    for elem in value:
                        p.pack_value(elem, T=elem_type)
                    return p.data

                @staticmethod
                def unpack(up):
                    value = list()
                    n = up.unpack_value(T=uint32_type)
                    if n is None:
                        return None
                    for _ in range(n):
                        elem = up.unpack_value(T=elem_type)
                        if elem is None:
                            return None
                        value.append(elem)
                    return value

            list_type._cache[elem_type] = list_type_inst

        return list_type._cache[elem_type]


class string_type:
    type_info = Pack(type_id.string_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, str)

    @staticmethod
    def pack(value):
        string_type.validate(value)
        p = Packer()
        p.pack_value(len(value), T=uint32_type)
        for ch in value:
            p.pack_value(ord(ch), T=uint8_type)
        return p.data

    @staticmethod
    def unpack(up):
        # todo: use StringIO for efficiency
        value = ""
        n = up.unpack_value(T=uint32_type)
        if n is None:
            return None
        for _ in range(n):
            ch = up.unpack_value(T=uint8_type)
            if ch is None:
                return None
            value += chr(ch)
        return value


def pack(value, T=None):
    T = T or resolve_type(value)
    return Packer().pack(value, T=T).data


def unpack_one(T, data):
    return Unpacker(data).unpack(T)


def unpack(Ts, data):
    if not isinstance(Ts, tuple):
        Ts = (Ts,)
    up = Unpacker(data)
    unpacked = tuple(up.unpack(T) for T in Ts)
    if any(value is None for value in unpacked):
        return None
    return unpacked


def test(value, T=None):
    T = T or resolve_type(value)
    print(f"input: {value!r}")

    packed = pack(value, T=T)
    print("packed:")
    packed.dump()

    unpacked = unpack_one(T, packed)
    if unpacked is None:
        print("failed to unpack")
    else:
        print(f"unpacked: {value!r}")


def main():
    test(5, T=uint32_type)
    print()
    test([1, 2, 3, 4, 5], T=list_type.of(float_type))
    print()
    test([-1, 1, -2, 2, -3, 3, -4, 4], T=list_type.of(int8_type))
    print()
    test("hello world")


if __name__ == "__main__":
    main()
