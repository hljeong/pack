import copy
from enum import Enum
import struct

from py_utils.dicts import EqDict, IdDict
from py_utils.sentinel import Sentinel

# todo: type annotations?
# todo: add switch for untyped vs typed packing


Unit = Sentinel("Unit")

Nullopt = Sentinel("Nullopt")


# todo: upper case these?
class type_id(Enum):
    type_info_type = 0x01
    unit_type = 0x02
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
    optional_type = 0x42
    tuple_type = 0x43


_cached_type = IdDict()


def resolve_type(value):
    def fail(reason=None):
        if reason:
            raise ValueError(f"{value!r} has unsupported type: {reason}")
        else:
            raise ValueError(f"{value!r} has unsupported type")

    if value in _cached_type:
        return _cached_type[value]

    elif isinstance(value, int):
        return int32_type

    elif isinstance(value, bool):
        return bool_type

    elif isinstance(value, list):
        if len(value) == 0:
            fail("list with length 0")

        elem_type = resolve_type(value[0])
        # todo: implement any(not castable(elem, elem_type) for ...)?
        if any(resolve_type(elem) is not elem_type for elem in value):
            fail("not all elements have the same type")

        return list_type.of(elem_type)

    elif isinstance(value, str):
        return string_type

    # todo: optional, tuple

    fail("not implemented")


def typed(value, T=None):
    value = copy.deepcopy(value)
    T = T or resolve_type(value)
    _cached_type[value] = T
    return value


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

    def pack(self, value, T=None):
        T = T or resolve_type(value)
        assert T is not None
        self._push(T.pack(value))
        return self

    def pack_typed(self, value, T=None):
        T = T or resolve_type(value)
        assert T is not None
        self._push(T.type_info)
        self.pack(value, T=T)
        return self


class Unpacker:
    class NotEnoughDataError(Exception):
        pass

    class BadDataTypeError(Exception):
        pass

    def __init__(self, data):
        self.data = Pack(data)
        self.idx = 0

    def consume(self, n):
        if self.idx + n > len(self.data):
            raise Unpacker.NotEnoughDataError(
                f"expecting {n} byte(s), only {len(self.data) - self.idx} available"
            )
        data = self.data[self.idx : self.idx + n]
        self.idx += n
        return data

    def unpack(self, T):
        return T.unpack(self)

    def unpack_typed(self, T):
        # todo: type name
        type_data = self.consume(len(T.type_info))
        if type_data != T.type_info:
            to_str = lambda data_bytes: " ".join(
                map(lambda byte: f"{byte:02x}", data_bytes)
            )
            raise Unpacker.BadDataTypeError(
                f"expecting type info {to_str(type_data)}, got {to_str(T.type_info)}"
            )
        return self.unpack(T)


class TypeInfo(Pack):
    def __init__(self, *comps):
        super().__init__(*comps)

    # todo: is this only possible in dynamically typed languages?
    # todo: is there an easier way to do this? (how to deal with custom type ids?)
    @property
    def T(self):
        if self.data[0] == 0x01:
            return type_info_type

        elif self.data[0] == 0x02:
            return unit_type

        elif self.data[0] == 0x10:
            return uint8_type

        elif self.data[0] == 0x11:
            return uint16_type

        elif self.data[0] == 0x12:
            return uint32_type

        elif self.data[0] == 0x13:
            return uint64_type

        elif self.data[0] == 0x18:
            return int8_type

        elif self.data[0] == 0x19:
            return int16_type

        elif self.data[0] == 0x1A:
            return int32_type

        elif self.data[0] == 0x1B:
            return int64_type

        elif self.data[0] == 0x20:
            return float_type

        elif self.data[0] == 0x20:
            return double_type

        elif self.data[0] == 0x30:
            return bool_type

        elif self.data[0] == 0x40:
            return list_type.of(TypeInfo(self.data[1:]).T)

        elif self.data[0] == 0x41:
            return string_type

        elif self.data[0] == 0x42:
            return optional_type.of(TypeInfo(self.data[1:]).T)

        elif self.data[0] == 0x43:
            # todo: ugly
            return tuple_type.of(
                *(
                    elem_type_info.T
                    for elem_type_info in list_type.of(type_info_type).unpack(
                        Unpacker(self.data[1:])
                    )
                )
            )

        else:
            raise ValueError(f"bad type info: {list(self.data)}")


# todo: reduce boilerplate
class type_info_type:
    type_info = TypeInfo(type_id.type_info_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, TypeInfo)

    @staticmethod
    def pack(value):
        type_info_type.validate(value)
        p = Packer()
        p.pack(len(value), T=uint8_type)
        for byte in value:
            p.pack(byte, T=uint8_type)
        return p.data

    @staticmethod
    def unpack(up):
        value = list()
        n = up.unpack(T=uint8_type)
        for _ in range(n):
            value.append(up.unpack(T=uint8_type))
        return TypeInfo(bytes(value))


class unit_type:
    type_info = TypeInfo(type_id.unit_type.value)

    @staticmethod
    def validate(value):
        assert value is Unit

    @staticmethod
    def pack(value):
        unit_type.validate(value)
        return Pack()

    @staticmethod
    def unpack(_):
        return Unit


class uint8_type:
    type_info = TypeInfo(type_id.uint8_type.value)

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
        return struct.unpack("<B", up.consume(1))[0]


class uint16_type:
    type_info = TypeInfo(type_id.uint16_type.value)

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
        return struct.unpack("<H", up.consume(2))[0]


class uint32_type:
    type_info = TypeInfo(type_id.uint32_type.value)

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
        return struct.unpack("<I", up.consume(4))[0]


class uint64_type:
    type_info = TypeInfo(type_id.uint64_type.value)

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
        return struct.unpack("<Q", up.consume(8))[0]


class int8_type:
    type_info = TypeInfo(type_id.int8_type.value)

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
        return struct.unpack("<b", up.consume(1))[0]


class int16_type:
    type_info = TypeInfo(type_id.int16_type.value)

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
        return struct.unpack("<h", up.consume(2))[0]


class int32_type:
    type_info = TypeInfo(type_id.int32_type.value)

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
        return struct.unpack("<i", up.consume(4))[0]


class int64_type:
    type_info = TypeInfo(type_id.int64_type.value)

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
        return struct.unpack("<q", up.consume(8))[0]


class float_type:
    type_info = TypeInfo(type_id.float_type.value)

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
        return struct.unpack("<f", up.consume(4))[0]


class double_type:
    type_info = TypeInfo(type_id.double_type.value)

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
        return struct.unpack("<d", up.consume(8))[0]


class bool_type:
    type_info = TypeInfo(type_id.bool_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, bool)

    @staticmethod
    def pack(value):
        bool_type.validate(value)
        return Pack(1 if value else 0)

    @staticmethod
    def unpack(up):
        return bool(up.consume(1)[0])


class list_type:
    _cache = dict()

    # todo: __getitem__ would be nice
    @staticmethod
    def of(elem_type):
        if elem_type not in list_type._cache:

            class list_type_inst:
                type_info = TypeInfo(type_id.list_type.value, elem_type.type_info)

                @staticmethod
                def validate(value):
                    assert isinstance(value, list)
                    for elem in value:
                        elem_type.validate(elem)

                @staticmethod
                def pack(value):
                    list_type_inst.validate(value)
                    p = Packer()
                    p.pack(len(value), T=uint32_type)
                    for elem in value:
                        p.pack(elem, T=elem_type)
                    return p.data

                @staticmethod
                def unpack(up):
                    value = list()
                    n = up.unpack(T=uint32_type)
                    for _ in range(n):
                        value.append(up.unpack(T=elem_type))
                    return value

            list_type._cache[elem_type] = list_type_inst

        return list_type._cache[elem_type]


class string_type:
    type_info = TypeInfo(type_id.string_type.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, str)

    @staticmethod
    def pack(value):
        string_type.validate(value)
        p = Packer()
        p.pack(len(value), T=uint32_type)
        for ch in value:
            p.pack(ord(ch), T=uint8_type)
        return p.data

    @staticmethod
    def unpack(up):
        # todo: use StringIO for efficiency
        value = ""
        n = up.unpack(T=uint32_type)
        for _ in range(n):
            value += chr(up.unpack(T=uint8_type))
        return value


class optional_type:
    _cache = dict()

    # todo: __getitem__ would be nice
    @staticmethod
    def of(elem_type):
        if elem_type not in optional_type._cache:

            class optional_type_inst:
                type_info = TypeInfo(type_id.optional_type.value, elem_type.type_info)

                @staticmethod
                def validate(value):
                    assert value is Nullopt or elem_type.validate(value)

                @staticmethod
                def pack(value):
                    optional_type_inst.validate(value)

                    p = Packer()

                    p.pack(value is not Nullopt, T=bool_type)

                    if value is not Nullopt:
                        p.pack(value, T=elem_type)

                    return p.data

                @staticmethod
                def unpack(up):
                    exists = up.unpack(T=bool_type)

                    if not exists:
                        return Nullopt

                    return up.unpack(T=elem_type)

            optional_type._cache[elem_type] = optional_type_inst

        return optional_type._cache[elem_type]


class tuple_type:
    _cache = EqDict()

    # todo: __getitem__ would be nice
    @staticmethod
    def of(*elem_types):
        if elem_types not in tuple_type._cache:

            class tuple_type_inst:
                type_info = TypeInfo(
                    type_id.tuple_type.value,
                    list_type.of(type_info_type).pack(
                        list(elem_type.type_info for elem_type in elem_types)
                    ),
                )

                @staticmethod
                def validate(value):
                    assert isinstance(value, tuple)
                    assert len(value) == len(elem_types)
                    for elem, elem_type in zip(value, elem_types):
                        elem_type.validate(elem)

                @staticmethod
                def pack(value):
                    tuple_type_inst.validate(value)

                    p = Packer()

                    for elem, elem_type in zip(value, elem_types):
                        p.pack(elem, T=elem_type)

                    return p.data

                @staticmethod
                def unpack(up):
                    return tuple(up.unpack(T=elem_type) for elem_type in elem_types)

            tuple_type._cache[elem_types] = tuple_type_inst

        return tuple_type._cache[elem_types]


def pack_one(value, T=None):
    return Packer().pack(value, T=T or resolve_type(value)).data


def pack(*values):
    p = Packer()
    for value in values:
        p.pack(value)
    return p.data


def unpack_one(T, data):
    return Unpacker(data).unpack(T)


def unpack(Ts, data):
    if not isinstance(Ts, tuple):
        Ts = (Ts,)
    up = Unpacker(data)
    return tuple_type.of(*Ts).unpack(up)
