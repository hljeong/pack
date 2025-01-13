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
class TypeId(Enum):
    TypeInfo = 0x01
    Unit = 0x02
    UInt8 = 0x10
    UInt16 = 0x11
    UInt32 = 0x12
    UInt64 = 0x13
    Int8 = 0x18
    Int16 = 0x19
    Int32 = 0x1A
    Int64 = 0x1B
    Float = 0x20
    Double = 0x21
    Bool = 0x30
    List = 0x40
    String = 0x41
    Optional = 0x42
    Tuple = 0x43


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
        return Int32Type

    elif isinstance(value, bool):
        return BoolType

    elif isinstance(value, list):
        if len(value) == 0:
            fail("list with length 0")

        elem_type = resolve_type(value[0])
        # todo: implement any(not castable(elem, elem_type) for ...)?
        if any(resolve_type(elem) is not elem_type for elem in value):
            fail("not all elements have the same type")

        return ListType.of(elem_type)

    elif isinstance(value, str):
        return StringType

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
            return TypeInfoType

        elif self.data[0] == 0x02:
            return UnitType

        elif self.data[0] == 0x10:
            return UInt8Type

        elif self.data[0] == 0x11:
            return UInt16Type

        elif self.data[0] == 0x12:
            return UInt32Type

        elif self.data[0] == 0x13:
            return UInt64Type

        elif self.data[0] == 0x18:
            return Int8Type

        elif self.data[0] == 0x19:
            return Int16Type

        elif self.data[0] == 0x1A:
            return Int32Type

        elif self.data[0] == 0x1B:
            return Int64Type

        elif self.data[0] == 0x20:
            return FloatType

        elif self.data[0] == 0x20:
            return DoubleType

        elif self.data[0] == 0x30:
            return BoolType

        elif self.data[0] == 0x40:
            return ListType.of(TypeInfo(self.data[1:]).T)

        elif self.data[0] == 0x41:
            return StringType

        elif self.data[0] == 0x42:
            return OptionalType.of(TypeInfo(self.data[1:]).T)

        elif self.data[0] == 0x43:
            # todo: ugly
            return TupleType.of(
                *(
                    elem_type_info.T
                    for elem_type_info in ListType.of(TypeInfoType).unpack(
                        Unpacker(self.data[1:])
                    )
                )
            )

        else:
            raise ValueError(f"bad type info: {list(self.data)}")


# todo: reduce boilerplate
class TypeInfoType:
    type_info = TypeInfo(TypeId.TypeInfo.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, TypeInfo)

    @staticmethod
    def pack(value):
        TypeInfoType.validate(value)
        p = Packer()
        p.pack(len(value), T=UInt8Type)
        for byte in value:
            p.pack(byte, T=UInt8Type)
        return p.data

    @staticmethod
    def unpack(up):
        value = list()
        n = up.unpack(T=UInt8Type)
        for _ in range(n):
            value.append(up.unpack(T=UInt8Type))
        return TypeInfo(bytes(value))


class UnitType:
    type_info = TypeInfo(TypeId.Unit.value)

    @staticmethod
    def validate(value):
        assert value is Unit

    @staticmethod
    def pack(value):
        UnitType.validate(value)
        return Pack()

    @staticmethod
    def unpack(_):
        return Unit


class UInt8Type:
    type_info = TypeInfo(TypeId.UInt8.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert 0 <= value < (1 << 8)

    @staticmethod
    def pack(value):
        UInt8Type.validate(value)
        return Pack(struct.pack("<B", value))

    @staticmethod
    def unpack(up):
        return struct.unpack("<B", up.consume(1))[0]


class UInt16Type:
    type_info = TypeInfo(TypeId.UInt16.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert 0 <= value < (1 << 16)

    @staticmethod
    def pack(value):
        UInt16Type.validate(value)
        return Pack(struct.pack("<H", value))

    @staticmethod
    def unpack(up):
        return struct.unpack("<H", up.consume(2))[0]


class UInt32Type:
    type_info = TypeInfo(TypeId.UInt32.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert 0 <= value < (1 << 32)

    @staticmethod
    def pack(value):
        UInt32Type.validate(value)
        return Pack(struct.pack("<I", value))

    @staticmethod
    def unpack(up):
        return struct.unpack("<I", up.consume(4))[0]


class UInt64Type:
    type_info = TypeInfo(TypeId.UInt64.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert 0 <= value < (1 << 64)

    @staticmethod
    def pack(value):
        UInt64Type.validate(value)
        return Pack(struct.pack("<Q", value))

    @staticmethod
    def unpack(up):
        return struct.unpack("<Q", up.consume(8))[0]


class Int8Type:
    type_info = TypeInfo(TypeId.Int8.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert -(1 << 7) <= value < (1 << 7)

    @staticmethod
    def pack(value):
        Int8Type.validate(value)
        return Pack(struct.pack("<b", value))

    @staticmethod
    def unpack(up):
        return struct.unpack("<b", up.consume(1))[0]


class Int16Type:
    type_info = TypeInfo(TypeId.Int16.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert -(1 << 15) <= value < (1 << 15)

    @staticmethod
    def pack(value):
        Int16Type.validate(value)
        return Pack(struct.pack("<h", value))

    @staticmethod
    def unpack(up):
        return struct.unpack("<h", up.consume(2))[0]


class Int32Type:
    type_info = TypeInfo(TypeId.Int32.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert -(1 << 31) <= value < (1 << 31)

    @staticmethod
    def pack(value):
        Int32Type.validate(value)
        return Pack(struct.pack("<i", value))

    @staticmethod
    def unpack(up):
        return struct.unpack("<i", up.consume(4))[0]


class Int64Type:
    type_info = TypeInfo(TypeId.Int64.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, int)
        assert -(1 << 63) <= value < (1 << 63)

    @staticmethod
    def pack(value):
        Int64Type.validate(value)
        return Pack(struct.pack("<q", value))

    @staticmethod
    def unpack(up):
        return struct.unpack("<q", up.consume(8))[0]


class FloatType:
    type_info = TypeInfo(TypeId.Float.value)

    # todo: possible to automate checking for castable types?
    @staticmethod
    def validate(value):
        assert isinstance(value, float) or isinstance(value, int)

    @staticmethod
    def pack(value):
        FloatType.validate(value)
        return Pack(struct.pack("<f", value))

    @staticmethod
    def unpack(up):
        return struct.unpack("<f", up.consume(4))[0]


class DoubleType:
    type_info = TypeInfo(TypeId.Double.value)

    # todo: possible to automate checking for castable types?
    @staticmethod
    def validate(value):
        assert isinstance(value, float) or isinstance(value, int)

    @staticmethod
    def pack(value):
        DoubleType.validate(value)
        return Pack(struct.pack("<d", value))

    @staticmethod
    def unpack(up):
        return struct.unpack("<d", up.consume(8))[0]


class BoolType:
    type_info = TypeInfo(TypeId.Bool.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, bool)

    @staticmethod
    def pack(value):
        BoolType.validate(value)
        return Pack(1 if value else 0)

    @staticmethod
    def unpack(up):
        return bool(up.consume(1)[0])


class ListType:
    # todo: should parametrized types use builtin dict?
    _cache = dict()

    # todo: __getitem__ would be nice
    @staticmethod
    def of(elem_type):
        if elem_type not in ListType._cache:

            class ListTypeInst:
                type_info = TypeInfo(TypeId.List.value, elem_type.type_info)

                @staticmethod
                def validate(value):
                    assert isinstance(value, list)
                    for elem in value:
                        elem_type.validate(elem)

                @staticmethod
                def pack(value):
                    ListTypeInst.validate(value)
                    p = Packer()
                    p.pack(len(value), T=UInt32Type)
                    for elem in value:
                        p.pack(elem, T=elem_type)
                    return p.data

                @staticmethod
                def unpack(up):
                    value = list()
                    n = up.unpack(T=UInt32Type)
                    for _ in range(n):
                        value.append(up.unpack(T=elem_type))
                    return value

            ListType._cache[elem_type] = ListTypeInst

        return ListType._cache[elem_type]


class StringType:
    type_info = TypeInfo(TypeId.String.value)

    @staticmethod
    def validate(value):
        assert isinstance(value, str)

    @staticmethod
    def pack(value):
        StringType.validate(value)
        p = Packer()
        p.pack(len(value), T=UInt32Type)
        for ch in value:
            p.pack(ord(ch), T=UInt8Type)
        return p.data

    @staticmethod
    def unpack(up):
        # todo: use StringIO for efficiency
        value = ""
        n = up.unpack(T=UInt32Type)
        for _ in range(n):
            value += chr(up.unpack(T=UInt8Type))
        return value


class OptionalType:
    _cache = dict()

    # todo: __getitem__ would be nice
    @staticmethod
    def of(elem_type):
        if elem_type not in OptionalType._cache:

            class OptionalTypeInst:
                type_info = TypeInfo(TypeId.Optional.value, elem_type.type_info)

                @staticmethod
                def validate(value):
                    assert value is Nullopt or elem_type.validate(value)

                @staticmethod
                def pack(value):
                    OptionalTypeInst.validate(value)

                    p = Packer()

                    p.pack(value is not Nullopt, T=BoolType)

                    if value is not Nullopt:
                        p.pack(value, T=elem_type)

                    return p.data

                @staticmethod
                def unpack(up):
                    exists = up.unpack(T=BoolType)

                    if not exists:
                        return Nullopt

                    return up.unpack(T=elem_type)

            OptionalType._cache[elem_type] = OptionalTypeInst

        return OptionalType._cache[elem_type]


class TupleType:
    _cache = EqDict()

    # todo: __getitem__ would be nice
    @staticmethod
    def of(*elem_types):
        if elem_types not in TupleType._cache:

            class TupleTypeInst:
                type_info = TypeInfo(
                    TypeId.Tuple.value,
                    ListType.of(TypeInfoType).pack(
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
                    TupleTypeInst.validate(value)

                    p = Packer()

                    for elem, elem_type in zip(value, elem_types):
                        p.pack(elem, T=elem_type)

                    return p.data

                @staticmethod
                def unpack(up):
                    return tuple(up.unpack(T=elem_type) for elem_type in elem_types)

            TupleType._cache[elem_types] = TupleTypeInst

        return TupleType._cache[elem_types]


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
    return TupleType.of(*Ts).unpack(up)
