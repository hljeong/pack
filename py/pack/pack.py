from copy import deepcopy
from enum import Enum
import struct

from py_utils.dicts import EqDict, IdDict, WithDefault
from py_utils.meta import meta, submetaclass_of
from py_utils.parametrize import parametrize, Parametrized
from py_utils.sentinel import Sentinel


# todo: type annotations?
# todo: add switch for untyped vs typed packing


Unit = Sentinel("Unit")

Nullopt = Sentinel("Nullopt")


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
    Union = 0x44


def deduce_type(value):
    def fail(reason=None):
        if reason:
            raise ValueError(f"{value!r} has unsupported type: {reason}")
        else:
            raise ValueError(f"{value!r} has unsupported type")

    if value in Type._cached:
        return Type._cached[value]

    elif isinstance(value, int):
        return Int32

    elif isinstance(value, bool):
        return Bool

    elif isinstance(value, list):
        if len(value) == 0:
            fail("list with length 0")

        T = deduce_type(value[0])
        # todo: implement any(not castable(elem, elem_type) for ...)?
        if any(deduce_type(elem) is not T for elem in value):
            fail("not all elements have the same type")

        return List[T]

    elif isinstance(value, str):
        return String

    elif isinstance(value, tuple):
        return Tuple[(deduce_type(elem) for elem in value)]

    # optional cannot be deduced
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

    @parametrize("T")
    def pack(self, value, T=None):
        T = T or deduce_type(value)
        assert T is not None
        self._push(T.pack(value))
        return self

    @parametrize("T")
    def pack_typed(self, value, T=None):
        T = T or deduce_type(value)
        assert T is not None
        self._push(T.type_info)
        self.pack[T](value)
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

    @parametrize()
    def unpack(self, T):
        return T.unpack(self)

    @parametrize()
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


def T(type_info):
    if isinstance(type_info, TypeInfo):
        return type_info.T

    return TypeInfo(type_info).T


class TypeInfo(Pack):
    def __init__(self, *comps):
        super().__init__(*comps)

    # todo: is this only possible in dynamically typed languages?
    # todo: is there an easier way to do this? (how to deal with custom type ids?)
    @property
    def T(self):
        # todo: possible to make TypeInfo a union type and simplify this?
        if self.data[0] == 0x01:
            return TypeInfoType

        elif self.data[0] == 0x02:
            return UnitType

        elif self.data[0] == 0x10:
            return UInt8

        elif self.data[0] == 0x11:
            return UInt16

        elif self.data[0] == 0x12:
            return UInt32

        elif self.data[0] == 0x13:
            return UInt64

        elif self.data[0] == 0x18:
            return Int8

        elif self.data[0] == 0x19:
            return Int16

        elif self.data[0] == 0x1A:
            return Int32

        elif self.data[0] == 0x1B:
            return Int64

        elif self.data[0] == 0x20:
            return Float

        elif self.data[0] == 0x20:
            return Double

        elif self.data[0] == 0x30:
            return Bool

        elif self.data[0] == 0x40:
            return List[T(self.data[1:])]

        elif self.data[0] == 0x41:
            return String

        elif self.data[0] == 0x42:
            return Optional[T(self.data[1:])]

        elif self.data[0] == 0x43:
            return Tuple[map(T, unpack[List[TypeInfoType]](self.data[1:]))]

        elif self.data[0] == 0x44:
            return Union[map(T, unpack[List[TypeInfoType]](self.data[1:]))]

        else:
            raise ValueError(f"bad type info: {list(self.data)}")


class TypeMeta(type):
    def __str__(cls):
        return cls.__name__

    def __repr__(cls):
        return f"type {cls}"


class Type(metaclass=TypeMeta):
    # todo: bug with string literals
    _cached = IdDict()

    def __new__(cls, value):
        value = deepcopy(value)
        Type._cached[value] = cls
        return value

    @classmethod
    def valid(cls, value):
        raise NotImplementedError

    @classmethod
    def pack_value(cls, value):
        raise NotImplementedError

    @classmethod
    def validate(cls, value):
        if not cls.valid(value):
            raise ValueError("todo")

    @classmethod
    def pack(cls, value):
        cls.validate(value)
        return cls.pack_value(value)


class ParametrizedType(submetaclass_of(Parametrized, Type)):
    _cache = WithDefault(IdDict(), lambda _: EqDict())

    @classmethod
    def of(cls, T_or_Ts):
        cache = ParametrizedType._cache[cls]
        # todo: cache should always hit except on the first lookup, confirm
        if T_or_Ts in cache:
            cache[cls] = cls[T_or_Ts]

        return cache[T_or_Ts]


# todo: nomenclature inconsistency...
class TypeInfoType(Type):
    type_info = TypeInfo(TypeId.TypeInfo.value)

    @classmethod
    def valid(cls, value):
        return isinstance(value, TypeInfo)

    @classmethod
    def pack_value(cls, value):
        p = Packer()
        p.pack[UInt8](len(value))
        for byte in value:
            p.pack[UInt8](byte)
        return p.data

    @classmethod
    def unpack(cls, up):
        value = list()
        n = up.unpack[UInt8]()
        for _ in range(n):
            value.append(up.unpack[UInt8]())
        return TypeInfo(bytes(value))


# todo: nomenclature inconsistency...
class UnitType:
    type_info = TypeInfo(TypeId.Unit.value)

    @classmethod
    def valid(cls, value):
        return value is Unit

    @classmethod
    def pack_value(cls, _):
        return Pack()

    @classmethod
    def unpack(cls, _):
        return Unit


def struct_pack(value, fmt):
    return Pack(struct.pack(fmt, value))


def struct_unpack(up, fmt):
    FMT_TO_BYTES = dict(b=1, B=1, h=2, H=2, i=4, I=4, q=8, Q=8, f=4, d=8)
    assert fmt in FMT_TO_BYTES
    return struct.unpack(f"<{fmt}", up.consume(FMT_TO_BYTES[fmt]))[0]


class UInt(Parametrized):
    @staticmethod
    def of(bitwidth):
        UINT_TYPE_ID = {
            8: TypeId.UInt8,
            16: TypeId.UInt16,
            32: TypeId.UInt32,
            64: TypeId.UInt64,
        }
        UINT_STRUCT_FMT = {8: "B", 16: "H", 32: "I", 64: "Q"}
        assert bitwidth in UINT_TYPE_ID

        @meta(__str__=lambda _: f"UInt{bitwidth}")
        class UIntInst(Type):
            type_info = TypeInfo(UINT_TYPE_ID[bitwidth].value)

            @classmethod
            def valid(cls, value):
                return isinstance(value, int) and 0 <= value < (1 << bitwidth)

            @classmethod
            def pack_value(cls, value):
                return struct_pack(value, UINT_STRUCT_FMT[bitwidth])

            @classmethod
            def unpack(cls, up):
                return struct_unpack(up, UINT_STRUCT_FMT[bitwidth])

        return UIntInst


UInt8 = UInt[8]
UInt16 = UInt[16]
UInt32 = UInt[32]
UInt64 = UInt[64]


class Int(Parametrized):
    @staticmethod
    def of(bitwidth):
        INT_TYPE_ID = {
            8: TypeId.Int8,
            16: TypeId.Int16,
            32: TypeId.Int32,
            64: TypeId.Int64,
        }
        INT_STRUCT_FMT = {8: "b", 16: "h", 32: "i", 64: "q"}
        assert bitwidth in INT_TYPE_ID

        @meta(__str__=lambda _: f"Int{bitwidth}")
        class IntInst(Type):
            type_info = TypeInfo(INT_TYPE_ID[bitwidth].value)

            @classmethod
            def valid(cls, value):
                return isinstance(value, int) and -(1 << (bitwidth - 1)) <= value < (
                    1 << (bitwidth - 1)
                )

            @classmethod
            def pack_value(cls, value):
                return struct_pack(value, INT_STRUCT_FMT[bitwidth])

            @classmethod
            def unpack(cls, up):
                return struct_unpack(up, INT_STRUCT_FMT[bitwidth])

        return IntInst


Int8 = Int[8]
Int16 = Int[16]
Int32 = Int[32]
Int64 = Int[64]


class Float(Type):
    type_info = TypeInfo(TypeId.Float.value)

    # todo: possible to automate checking for castable types?
    @classmethod
    def valid(cls, value):
        return isinstance(value, float) or isinstance(value, int)

    @classmethod
    def pack_value(cls, value):
        return struct_pack(value, "f")

    @classmethod
    def unpack(cls, up):
        return struct_unpack(up, "f")


class Double(Type):
    type_info = TypeInfo(TypeId.Double.value)

    # todo: possible to automate checking for castable types?
    @classmethod
    def valid(cls, value):
        return isinstance(value, float) or isinstance(value, int)

    @classmethod
    def pack_value(cls, value):
        return struct_pack(value, "d")

    @classmethod
    def unpack(cls, up):
        return struct_unpack(up, "d")


class Bool(Type):
    type_info = TypeInfo(TypeId.Bool.value)

    @classmethod
    def valid(cls, value):
        return isinstance(value, bool)

    @classmethod
    def pack_value(cls, value):
        return Pack(1 if value else 0)

    @classmethod
    def unpack(cls, up):
        return bool(up.consume(1)[0])


class List(ParametrizedType):
    @classmethod
    def of(cls, T):  # type: ignore  # todo: [0] type check error fixable?
        @meta(__str__=lambda _: f"List[{T}]")
        class ListInst(Type):
            type_info = TypeInfo(TypeId.List.value, T.type_info)

            @classmethod
            def valid(cls, value):
                return isinstance(value, list) and all(T.valid(elem) for elem in value)

            @classmethod
            def pack_value(cls, value):
                p = Packer()
                p.pack[UInt32](len(value))
                for elem in value:
                    p.pack[T](elem)
                return p.data

            @classmethod
            def unpack(cls, up):
                value = list()
                n = up.unpack[UInt32]()
                for _ in range(n):
                    value.append(up.unpack[T]())
                return value

        return ListInst


class String(Type):
    type_info = TypeInfo(TypeId.String.value)

    @classmethod
    def valid(cls, value):
        return isinstance(value, str)

    @classmethod
    def pack_value(cls, value):
        p = Packer()
        p.pack[UInt32](len(value))
        for ch in value:
            p.pack[UInt8](ord(ch))
        return p.data

    @classmethod
    def unpack(cls, up):
        # todo: use StringIO for efficiency
        value = ""
        n = up.unpack[UInt32]()
        for _ in range(n):
            value += chr(up.unpack[UInt8]())
        return value


class Optional(ParametrizedType):
    @classmethod
    def of(cls, T):  # type: ignore  # todo: see [0]
        @meta(__str__=lambda _: f"Optional[{T}]")
        class OptionalInst(Type):
            type_info = TypeInfo(TypeId.Optional.value, T.type_info)

            @classmethod
            def valid(cls, value):
                return value is Nullopt or T.valid(value)

            @classmethod
            def pack_value(cls, value):
                p = Packer()

                p.pack[Bool](value is not Nullopt)

                if value is not Nullopt:
                    p.pack[T](value)

                return p.data

            @classmethod
            def unpack(cls, up):
                exists = up.unpack[Bool]()

                if not exists:
                    return Nullopt

                return up.unpack[T]()

        return OptionalInst


class Tuple(ParametrizedType):
    @classmethod
    def of(cls, Ts):  # type: ignore  # todo: see [0]
        if not isinstance(Ts, tuple):
            Ts = (Ts,)

        @meta(__str__=lambda _: f"Tuple[{', '.join(map(str, Ts))}]")
        class TupleInst(Type):
            type_info = TypeInfo(
                TypeId.Tuple.value,
                List[TypeInfoType].pack([T.type_info for T in Ts]),
            )

            @classmethod
            def valid(cls, value):
                return (
                    isinstance(value, tuple)
                    and len(value) == len(Ts)
                    and all(T.valid(elem) for T, elem in zip(Ts, value))
                )

            @classmethod
            def pack_value(cls, value):
                p = Packer()

                for T, elem in zip(Ts, value):
                    p.pack[T](elem)

                return p.data

            @classmethod
            def unpack(cls, up):
                return tuple(up.unpack[T]() for T in Ts)

        return TupleInst


class Union(ParametrizedType):
    @classmethod
    def of(cls, Ts):  # type: ignore  # todo: see [0]
        if not isinstance(Ts, tuple):
            Ts = (Ts,)

        @meta(__str__=lambda _: f"Union[{', '.join(map(str, Ts))}]")
        class UnionInst(Type):
            type_info = TypeInfo(
                TypeId.Union.value,
                List[TypeInfoType].pack([T.type_info for T in Ts]),
            )

            @classmethod
            def valid(cls, value):
                return sum(T.valid(value) for T in Ts) == 1

            @classmethod
            def pack_value(cls, value):
                p = Packer()

                # exactly one branch should execute
                for T in Ts:
                    if T.valid(value):
                        p.pack[TypeInfoType](T.type_info)
                        p.pack[T](value)

                return p.data

            @classmethod
            def unpack(cls, up):
                return up.unpack[up.unpack[TypeInfoType]().T]()

        return UnionInst


@parametrize("T")
def pack_one(value, T=None):
    return Packer().pack[T or deduce_type(value)](value).data


# todo: figure out how to parametrize this
def pack(*values):
    p = Packer()
    for value in values:
        p.pack(value)
    return p.data


@parametrize()
def unpack_one(T, data):
    return Unpacker(data).unpack(T)


@parametrize()
def unpack(Ts, data):
    if not isinstance(Ts, tuple):
        Ts = (Ts,)
    up = Unpacker(data)
    return Tuple[Ts].unpack(up)
