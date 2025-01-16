#pragma once

#include <cstdint>
#include <cstdio>
#include <initializer_list>
#include <optional>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

#include "cpp_utils/fmt/fmt.h"

namespace pack {

// todo: add logger hook?
// todo: add switch for untyped vs typed packing

class Unit : std::tuple<> {};

enum class TypeId : uint8_t {
  TypeInfo = 0x01,
  Unit = 0x02,
  UInt8 = 0x10,
  UInt16 = 0x11,
  UInt32 = 0x12,
  UInt64 = 0x13,
  Int8 = 0x18,
  Int16 = 0x19,
  Int32 = 0x1a,
  Int64 = 0x1b,
  Float = 0x20,
  Double = 0x21,
  Bool = 0x30,
  List = 0x40,
  String = 0x41,
  Optional = 0x42,
  Tuple = 0x43,
};

using Bytes = std::vector<uint8_t>;

class Pack : public Bytes {
public:
  Pack() = default;

  template <typename... Ts> Pack(Ts... comps) : Bytes() {
    (
        [&]() {
          // todo: not a pretty patch to get enum class to work
          if constexpr (std::is_same_v<decltype(comps), TypeId>) {
            push_back(static_cast<uint8_t>(comps));
          } else {
            const Bytes comp_data{comps};
            insert(end(), comp_data.begin(), comp_data.end());
          };
        }(),
        ...);
  }

  Pack(std::initializer_list<uint8_t> init) : Bytes(init) {}

  void dump() const {
    uint32_t i = 0;
    for (const auto &byte : *this) {
      if (i) {
        printf("%c", " \n"[!(i % 8)]);
      }
      i++;
      printf("%02x", byte);
    }
    printf("\n");
  }
};

// forward declarations
class Unpacker;
template <typename T> T unpack_bits(Unpacker &up);

class TypeInfo : public Pack {
public:
  TypeInfo() = default;

  template <typename... Ts> TypeInfo(Ts... comps) : Pack(comps...) {}

  TypeInfo(std::initializer_list<uint8_t> init) : Pack(init) {}
};

template <typename T> Pack pack_bits(const T &value) {
  const uint8_t *value_ptr = reinterpret_cast<const uint8_t *>(&value);
  return Pack(Bytes(value_ptr, value_ptr + sizeof(T)));
}

template <typename T> struct Type {
  static const TypeInfo type_info;
  // Directly pack and unpack the bit representation by default
  // This necessarily needs to be specialized for complex types
  inline static auto pack(const T &value) { return pack_bits(value); }
  inline static auto unpack(Unpacker &up) { return unpack_bits<T>(up); }
};
template <typename T> const TypeInfo type_info = Type<T>::type_info;

class Packer {
public:
  template <typename T> Packer &pack(const T &value) {
    push(Type<T>::pack(value));
    return *this;
  }

  template <typename T> Packer &pack_typed(const T &value) {
    push(type_info<T>);
    pack(value);
    return *this;
  }

  // todo: can this be private?
  void push(const Bytes &data) {
    m_data.insert(m_data.end(), data.begin(), data.end());
  }

  const Pack &operator*() { return m_data; }

private:
  Pack m_data;
};

class Unpacker {
public:
  class NotEnoughDataError : public std::exception,
                             public std::nested_exception {
  public:
    explicit NotEnoughDataError(const std::string &message)
        : m_message(message) {}

    const char *what() const noexcept override { return m_message.c_str(); };

  private:
    std::string m_message;
  };

  class BadDataTypeError : public std::exception {
  public:
    explicit BadDataTypeError(const std::string &message)
        : m_message(message) {}

    const char *what() const noexcept override { return m_message.c_str(); };

  private:
    std::string m_message;
  };

  Unpacker(const Bytes &data) : m_data(data) {};

  template <typename T> T unpack() { return Type<T>::unpack(*this); }

  template <typename T> T unpack_typed() {
    // todo: type name
    const Bytes &type_data = consume(type_info<T>.size());
    if (type_data != type_info<T>) {
      std::stringstream s;
      s << "expecting type info ";
      for (const auto byte : type_info<T>) {
        char buf[3];
        snprintf(buf, 3, "%02x", byte);
        s << buf;
      }
      s << ", got ";
      for (const auto byte : type_info<T>) {
        char buf[3];
        snprintf(buf, 3, "%02x", byte);
        s << buf;
      }
      throw BadDataTypeError(s.str());
    }
    return unpack<T>();
  }

  // todo: can this be private?
  Pack consume(std::size_t n) {
    if (m_idx + n > m_data.size()) {
      std::stringstream s;
      s << "expecting " << std::to_string(n) << " byte(s), only "
        << std::to_string(m_data.size() - m_idx) << " available";
      throw std::runtime_error(s.str());
    }
    const Pack data(Bytes(m_data.begin() + m_idx, m_data.begin() + m_idx + n));
    m_idx += n;
    return data;
  }

  // todo: is this needed?
  Pack consume() { return consume(m_data.size() - m_idx); }

private:
  Pack m_data;
  uint32_t m_idx = 0;
};

template <typename T> T unpack_bits(Unpacker &up) {
  const auto data = up.consume(sizeof(T));

  T value{};
  for (uint32_t i = 0; i < sizeof(T); ++i) {
    *(reinterpret_cast<uint8_t *>(&value) + i) = data[i];
  }

  return value;
}

template <> struct Type<TypeInfo> {
  inline static const TypeInfo type_info = {TypeId::TypeInfo};

  static Pack pack(const TypeInfo &value) {
    Packer p;

    p.pack<uint8_t>(value.size());

    for (const auto &byte : value) {
      p.pack(byte);
    }

    return *p;
  }

  static TypeInfo unpack(Unpacker &up) {
    const auto n = up.unpack<uint8_t>();

    TypeInfo value;
    for (uint8_t i = 0; i < n; ++i) {
      value.push_back(up.unpack<uint8_t>());
    }

    return value;
  }
};

template <> struct Type<Unit> {
  inline static const TypeInfo type_info = {TypeId::Unit};

  static Pack pack(const Unit &value) { return {}; }

  static Unit unpack(Unpacker &up) { return {}; }
};

template <> inline const TypeInfo Type<uint8_t>::type_info = {TypeId::UInt8};

template <> inline const TypeInfo Type<uint16_t>::type_info = {TypeId::UInt16};

template <> inline const TypeInfo Type<uint32_t>::type_info = {TypeId::UInt32};

template <> inline const TypeInfo Type<uint64_t>::type_info = {TypeId::UInt64};

template <> inline const TypeInfo Type<int8_t>::type_info = {TypeId::Int8};

template <> inline const TypeInfo Type<int16_t>::type_info = {TypeId::Int16};

template <> inline const TypeInfo Type<int32_t>::type_info = {TypeId::Int32};

template <> inline const TypeInfo Type<int64_t>::type_info = {TypeId::Int64};

template <> inline const TypeInfo Type<float>::type_info = {TypeId::Float};

template <> inline const TypeInfo Type<double>::type_info = {TypeId::Double};

template <> inline const TypeInfo Type<bool>::type_info = {TypeId::Bool};

template <typename T> struct Type<std::vector<T>> {
  inline static const TypeInfo type_info =
      TypeInfo(TypeId::List, pack::type_info<T>);

  static Pack pack(const std::vector<T> &value) {
    Packer p;

    p.pack<uint32_t>(value.size());

    for (const auto &elem : value) {
      p.pack(elem);
    }

    return *p;
  }

  static std::vector<T> unpack(Unpacker &up) {
    const auto n = up.unpack<uint32_t>();

    std::vector<T> value;
    for (uint32_t i = 0; i < n; ++i) {
      value.push_back(up.unpack<T>());
    }

    return value;
  }
};

template <> struct Type<std::string> {
  inline static const TypeInfo type_info = {TypeId::String};

  static Pack pack(const std::string &value) {
    Packer p;

    p.pack<uint32_t>(value.size());

    for (const auto &ch : value) {
      p.pack<uint8_t>(ch);
    }

    return *p;
  }

  static std::string unpack(Unpacker &up) {
    const auto n = up.unpack<uint32_t>();

    std::stringstream value;
    for (uint32_t i = 0; i < n; ++i) {
      value << static_cast<char>(up.unpack<uint8_t>());
    }

    return value.str();
  }
};

template <> struct Type<std::string_view> : Type<std::string> {
  static Pack pack(std::string_view value) {
    Packer p;

    p.pack<uint32_t>(value.size());

    for (const auto &ch : value) {
      p.pack<uint8_t>(ch);
    }

    return *p;
  }
};

template <typename T> struct Type<std::optional<T>> {
  inline static const TypeInfo type_info =
      TypeInfo(TypeId::Optional, pack::type_info<T>);

  static Pack pack(const std::optional<T> &value) {
    Packer p;

    p.pack(!!value);

    if (value) {
      p.pack(*value);
    }

    return *p;
  }

  static std::optional<T> unpack(Unpacker &up) {
    const auto exists = up.unpack<bool>();

    if (!exists) {
      return std::optional<T>(std::nullopt);
    }

    return up.unpack<T>();
  }
};

template <typename... Ts> struct Type<std::tuple<Ts...>> {
  inline static const TypeInfo type_info =
      TypeInfo(TypeId::Tuple,
               Type<std::vector<TypeInfo>>::pack({pack::type_info<Ts>...}));

  static Pack pack(const std::tuple<Ts...> &value) {
    Packer p;

    std::apply([&](const Ts &...value_) { (p.pack<Ts>(value_), ...); }, value);

    return *p;
  }

  static std::tuple<Ts...> unpack(Unpacker &up) { return {up.unpack<Ts>()...}; }
};

template <typename T> inline static Pack pack_one(const T &value) {
  return *Packer().pack(value);
}

template <typename... Ts> inline static Pack pack(const Ts &...values) {
  Packer p;

  (p.pack(values), ...);

  return *p;
}

template <typename T> inline static T unpack_one(const Bytes &data) {
  return Unpacker(data).unpack<T>();
}

template <typename... Ts>
inline static std::tuple<Ts...> unpack(const Bytes &data) {
  Unpacker up(data);
  return Type<std::tuple<Ts...>>::unpack(up);
}

}; // namespace pack
