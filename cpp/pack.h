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

class Unit : std::tuple<> {};

enum type_id : uint8_t {
  type_info_type = 0x01,
  unit_type = 0x02,
  uint8_type = 0x10,
  uint16_type = 0x11,
  uint32_type = 0x12,
  uint64_type = 0x13,
  int8_type = 0x18,
  int16_type = 0x19,
  int32_type = 0x1a,
  int64_type = 0x1b,
  float_type = 0x20,
  double_type = 0x21,
  bool_type = 0x30,
  list_type = 0x40,
  string_type = 0x41,
  optional_type = 0x42,
};

using Bytes = std::vector<uint8_t>;

class Pack : public Bytes {
public:
  Pack() : Bytes() {}

  template <typename... Ts> Pack(Ts... comps) : Bytes() {
    (
        [&]() {
          const Bytes comp_data{comps};
          insert(end(), comp_data.begin(), comp_data.end());
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
template <typename T> std::optional<T> unpack_bits(Unpacker &up);

class TypeInfo : public Pack {
public:
  TypeInfo() : Pack() {}

  template <typename... Ts> TypeInfo(Ts... comps) : Pack(comps...) {}

  TypeInfo(std::initializer_list<uint8_t> init) : Pack(init) {}
};

template <typename T> Pack pack_bits(const T &value) {
  const uint8_t *value_ptr = reinterpret_cast<const uint8_t *>(&value);
  return Pack(Bytes(value_ptr, value_ptr + sizeof(T)));
}

template <typename T> struct type {
  static const TypeInfo type_info;
  // Directly pack and unpack the bit representation by default
  // This necessarily needs to be specialized for complex types
  inline static auto pack(const T &value) { return pack_bits(value); }
  inline static auto unpack(Unpacker &up) { return unpack_bits<T>(up); }
};
template <typename T> const TypeInfo type_info = type<T>::type_info;

class Packer {
public:
  // todo: pack_value() to be default pack(), add pack_type()
  template <typename T> Packer &pack_value(const T &value) {
    push(type<T>::pack(value));
    return *this;
  }

  template <typename T> Packer &pack(const T &value) {
    push(type_info<T>);
    pack_value(value);
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
  Unpacker(const Bytes &data) : m_data(data) {};

  // todo: see comment about pack_value() above
  template <typename T> std::optional<T> unpack_value() {
    return type<T>::unpack(*this);
  }

  template <typename T> std::optional<T> unpack() {
    return expect(type_info<T>) ? unpack_value<T>() : std::nullopt;
  }

  // todo: can this be private?
  std::optional<Pack> consume(std::size_t n) {
    if (m_idx + n > m_data.size()) {
      return std::nullopt;
    }
    const Pack data(Bytes(m_data.begin() + m_idx, m_data.begin() + m_idx + n));
    m_idx += n;
    return data;
  }

  // todo: is this needed?
  Pack consume() { return *consume(m_data.size() - m_idx); }

private:
  bool expect(const Bytes &expected) {
    return consume(expected.size()) == expected;
  }

  Pack m_data;
  uint32_t m_idx = 0;
};

template <typename T> std::optional<T> unpack_bits(Unpacker &up) {
  const auto data_opt = up.consume(sizeof(T));
  if (!data_opt) {
    return std::nullopt;
  }

  T value{};
  for (uint32_t i = 0; i < sizeof(T); ++i) {
    *(reinterpret_cast<uint8_t *>(&value) + i) = (*data_opt)[i];
  }

  return value;
}

template <> struct type<TypeInfo> {
  inline static const TypeInfo type_info = {type_info_type};

  static Pack pack(const TypeInfo &value) {
    Packer p;

    p.pack_value<uint8_t>(value.size());

    for (const auto &byte : value) {
      p.pack_value(byte);
    }

    return *p;
  }

  static std::optional<TypeInfo> unpack(Unpacker &up) {
    const auto n_opt = up.unpack_value<uint8_t>();
    if (!n_opt) {
      return std::nullopt;
    }

    TypeInfo value;
    for (uint8_t i = 0; i < *n_opt; ++i) {
      const auto byte_opt = up.unpack_value<uint8_t>();
      if (!byte_opt) {
        return std::nullopt;
      }

      value.push_back(*byte_opt);
    }

    return value;
  }
};

template <> struct type<Unit> {
  inline static const TypeInfo type_info = {unit_type};

  static Pack pack(const Unit &value) { return {}; }

  static Unit unpack(Unpacker &up) { return {}; }
};

template <> const TypeInfo type<uint8_t>::type_info = {uint8_type};

template <> const TypeInfo type<uint16_t>::type_info = {uint16_type};

template <> const TypeInfo type<uint32_t>::type_info = {uint32_type};

template <> const TypeInfo type<uint64_t>::type_info = {uint64_type};

template <> const TypeInfo type<int8_t>::type_info = {int8_type};

template <> const TypeInfo type<int16_t>::type_info = {int16_type};

template <> const TypeInfo type<int32_t>::type_info = {int32_type};

template <> const TypeInfo type<int64_t>::type_info = {int64_type};

template <> const TypeInfo type<float>::type_info = {float_type};

template <> const TypeInfo type<double>::type_info = {double_type};

template <> const TypeInfo type<bool>::type_info = {bool_type};

template <typename T> struct type<std::vector<T>> {
  inline static const TypeInfo type_info =
      TypeInfo(list_type, pack::type_info<T>);

  static Pack pack(const std::vector<T> &value) {
    Packer p;

    p.pack_value<uint32_t>(value.size());

    for (const auto &elem : value) {
      p.pack_value(elem);
    }

    return *p;
  }

  static std::optional<std::vector<T>> unpack(Unpacker &up) {
    const auto n_opt = up.unpack_value<uint32_t>();
    if (!n_opt) {
      return std::nullopt;
    }

    std::vector<T> value;
    for (uint32_t i = 0; i < *n_opt; ++i) {
      const auto elem_opt = up.unpack_value<T>();
      if (!elem_opt) {
        return std::nullopt;
      }

      value.push_back(*elem_opt);
    }

    return value;
  }
};

template <> struct type<std::string> {
  inline static const TypeInfo type_info = {string_type};

  static Pack pack(const std::string &value) {
    Packer p;

    p.pack_value<uint32_t>(value.size());

    for (const auto &ch : value) {
      p.pack_value<uint8_t>(ch);
    }

    return *p;
  }

  static std::optional<std::string> unpack(Unpacker &up) {
    const auto n_opt = up.unpack_value<uint32_t>();
    if (!n_opt) {
      return std::nullopt;
    }

    std::stringstream value;
    for (uint32_t i = 0; i < *n_opt; ++i) {
      const auto ch_opt = up.unpack_value<uint8_t>();
      if (!ch_opt) {
        return std::nullopt;
      }

      value << static_cast<char>(*ch_opt);
    }

    return value.str();
  }
};
template <typename T> struct type<std::optional<T>> {
  inline static const TypeInfo type_info =
      TypeInfo(optional_type, pack::type_info<T>);

  static Pack pack(const std::optional<T> &value) {
    Packer p;

    p.pack_value(!!value);

    if (value) {
      p.pack_value(*value);
    }

    return *p;
  }

  static std::optional<std::optional<T>> unpack(Unpacker &up) {
    const auto exists_opt = up.unpack_value<bool>();
    if (!exists_opt) {
      return std::nullopt;
    }

    if (!*exists_opt) {
      return std::make_optional(std::optional<T>(std::nullopt));
    }

    const auto value_opt = up.unpack_value<T>();
    if (!value_opt) {
      return std::nullopt;
    }

    return *value_opt;
  }
};

template <typename T> inline static Pack pack_one(const T &value) {
  return *Packer().pack(value);
}

template <typename... Ts> inline static Pack pack(const Ts &...values) {
  Packer p;
  (p.pack(values), ...);
  return *p;
}

template <typename T>
inline static std::optional<T> unpack_one(const Bytes &data) {
  return Unpacker(data).unpack<T>();
}

template <typename... Ts>
inline static std::optional<std::tuple<Ts...>> unpack(const Bytes &data) {
  Unpacker up(data);
  const std::tuple<std::optional<Ts>...> value_opts = {up.unpack<Ts>()...};
  const auto disjunct = [](const Ts... value_opts) {
    return (!value_opts || ...)
               ? std::nullopt
               : std::make_optional(std::make_tuple(*value_opts...));
  };
  return std::apply(disjunct, value_opts);
}

}; // namespace pack
