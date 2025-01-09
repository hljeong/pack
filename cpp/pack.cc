#include <cstdint>
#include <cstdio>
#include <initializer_list>
#include <optional>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

namespace fmt {

template <typename T, std::enable_if_t<std::is_arithmetic_v<T>, bool> = true>
std::string repr(T value) {
  return std::to_string(value);
}

std::string repr(bool value) { return value ? "true" : "false"; }

// todo: implement tuple
std::string repr(const std::tuple<> &) { return "unit"; }

template <typename T> std::string repr(const std::vector<T> &value) {
  const std::size_t n = value.size();
  std::stringstream s;
  s << "[";
  for (std::size_t i = 0; i < n; ++i) {
    if (i) {
      s << ", ";
    }
    s << repr(value[i]);
  }
  s << "]";
  return s.str();
}

std::string repr(const std::string &value) {
  std::stringstream s;
  s << "\"" << value << "\"";
  return s.str();
}

}; // namespace fmt

namespace pack {
enum type_id : uint8_t {
  type_type = 0x01,
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
};

using Bytes = std::vector<uint8_t>;

class Pack : public Bytes {
public:
  Pack() : Bytes() {}

  template <typename... Ts> Pack(Ts... comps) : Bytes() {
    Bytes comp_data;
    (
        [&]() {
          const Bytes comp_data{comps};
          insert(end(), comp_data.begin(), comp_data.end());
        }(),
        ...);
  }

  Pack(std::initializer_list<uint8_t> init) : Bytes(init) {}

  inline void dump() const {
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

class Unpacker;
template <typename T> inline static Pack pack_bits(const T &value);
template <typename T> inline static std::optional<T> unpack_bits(Unpacker &up);
template <typename T> struct type {
  static const Pack type_info;
  // Directly pack and unpack the bit representation by default
  // This necessarily needs to be specialized for complex types
  inline static Pack pack(const T &value) { return pack_bits(value); }
  inline static std::optional<T> unpack(Unpacker &up) {
    return unpack_bits<T>(up);
  }
};
template <typename T> const Pack type_info = type<T>::type_info;

class Packer {
public:
  template <typename T> inline Packer &pack_value(const T &value) {
    push(type<T>::pack(value));
    return *this;
  }

  template <typename T> inline Packer &pack(const T &value) {
    push(type_info<T>);
    pack_value(value);
    return *this;
  }

  inline void push(const Bytes &data) {
    m_data.insert(m_data.end(), data.begin(), data.end());
  }

  inline const Pack &operator*() { return m_data; }

private:
  Pack m_data{};
};

class Unpacker {
public:
  Unpacker(const Bytes &data) : m_data(data) {};

  template <typename T> inline std::optional<T> unpack_value() {
    return type<T>::unpack(*this);
  }

  template <typename T> inline std::optional<T> unpack() {
    return expect(type_info<T>) ? unpack_value<T>() : std::nullopt;
  }

  inline std::optional<Pack> consume(uint32_t n) {
    if (m_idx + n > m_data.size()) {
      return std::nullopt;
    }
    const Pack data(Bytes(m_data.begin() + m_idx, m_data.begin() + m_idx + n));
    m_idx += n;
    return data;
  }

private:
  inline bool expect(const Bytes &expected) {
    return consume(expected.size()) == expected;
  }

  Pack m_data;
  uint32_t m_idx = 0;
};

template <typename T> inline static Pack pack_bits(const T &value) {
  const uint8_t *value_ptr = reinterpret_cast<const uint8_t *>(&value);
  return Pack(Bytes(value_ptr, value_ptr + sizeof(T)));
}

template <typename T> inline static std::optional<T> unpack_bits(Unpacker &up) {
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

template <> const Pack type<uint8_t>::type_info = {uint8_type};
template <> const Pack type<uint16_t>::type_info = {uint16_type};
template <> const Pack type<uint32_t>::type_info = {uint32_type};
template <> const Pack type<uint64_t>::type_info = {uint64_type};
template <> const Pack type<int8_t>::type_info = {int8_type};
template <> const Pack type<int16_t>::type_info = {int16_type};
template <> const Pack type<int32_t>::type_info = {int32_type};
template <> const Pack type<int64_t>::type_info = {int64_type};
template <> const Pack type<float>::type_info = {float_type};
template <> const Pack type<double>::type_info = {double_type};
template <> const Pack type<bool>::type_info = {bool_type};

template <typename T, std::size_t N> struct type<T[N]> {
  inline static const Pack type_info = Pack(list_type, pack::type_info<T>);
  static Pack pack(const T (&value)[N]) {
    Packer p{};
    p.pack_value<uint32_t>(N);
    for (const auto &elem : value) {
      p.pack_value(elem);
    }
    return *p;
  }
  static std::optional<T[N]> unpack(Unpacker *up) = delete;
};

template <typename T> struct type<std::vector<T>> {
  inline static const Pack type_info = Pack(list_type, pack::type_info<T>);
  static Pack pack(const std::vector<T> &value) {
    Packer p{};
    p.pack_value<uint32_t>(value.size());
    for (const auto &elem : value) {
      p.pack_value(elem);
    }
    return *p;
  }
  static std::optional<std::vector<T>> unpack(Unpacker &up) {
    std::vector<T> value{};
    const auto n_opt = up.unpack_value<uint32_t>();
    if (!n_opt) {
      return std::nullopt;
    }
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
  inline static const Pack type_info = {string_type};
  static Pack pack(const std::string &value) {
    Packer p{};
    p.pack_value<uint32_t>(value.size());
    for (const auto &ch : value) {
      p.pack_value<uint8_t>(ch);
    }
    return *p;
  }
  static std::optional<std::string> unpack(Unpacker &up) {
    std::stringstream value{};
    const auto n_opt = up.unpack_value<uint32_t>();
    if (!n_opt) {
      return std::nullopt;
    }
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

template <typename... Ts> inline static Pack pack(const Ts &...values) {
  Packer p{};
  (p.pack(values), ...);
  return *p;
}

template <typename T>
inline static std::optional<T> unpack_one(const Bytes &data) {
  return Unpacker(data).unpack<T>();
}

template <typename... Ts, std::size_t... Idx>
inline static std::optional<std::tuple<Ts...>>
process_unpacked(const std::tuple<std::optional<Ts>...> &unpacked,
                 std::index_sequence<Idx...>) {
  return (!std::get<Idx>(unpacked) || ...)
             ? std::nullopt
             : std::make_optional<std::tuple<Ts...>>(
                   {*std::get<Idx>(unpacked)...});
}

template <typename... Ts>
inline static std::optional<std::tuple<Ts...>>
process_unpacked(const std::tuple<std::optional<Ts>...> &unpacked) {
  return process_unpacked(unpacked, std::index_sequence_for<Ts...>{});
}

template <typename... Ts>
inline static std::optional<std::tuple<Ts...>> unpack(const Bytes &data) {
  Unpacker up(data);
  const std::tuple<std::optional<Ts>...> unpacked = {up.unpack<Ts>()...};
  return process_unpacked(unpacked);
}
}; // namespace pack

template <typename T> void test_pack_only(const T &value) {
  printf("input: %s\n", fmt::repr(value).c_str());

  const auto packed = pack::pack(value);
  printf("packed:\n");
  packed.dump();
}

template <typename T> void test(const T &value) {
  printf("input: %s\n", fmt::repr(value).c_str());

  const auto packed = pack::pack(value);
  printf("packed:\n");
  packed.dump();

  const auto unpacked = pack::unpack_one<T>(packed);
  if (!unpacked)
    printf("failed to unpack\n");
  else {
    printf("unpacked: %s\n", fmt::repr(*unpacked).c_str());
  }
}

int main() {
  test<uint32_t>(5);
  printf("\n");
  test<std::vector<int8_t>>({-1, 1, -2, 2, -3, 3, -4, 4});
  printf("\n");
  test(std::string("hello world"));
}
