#include <cstdint>
#include <type_traits>
#include <vector>

namespace pack {
// using std::false_type;
// using std::true_type;
//
// template <typename> struct is_list_t : false_type {};
// template <typename T, std::size_t N> struct is_list_t<T[N]> : true_type {};
// template <typename T> struct is_list_t<std::vector<T>> : true_type {};
// template <typename T, std::size_t N>
// struct is_list_t<std::array<T, N>> : true_type {};
// template <typename T> constexpr bool is_list = is_list_t<T>::value;

enum type_id_t : uint8_t {
  uint8 = 0x10,
  uint16 = 0x11,
  uint32 = 0x12,
  uint64 = 0x13,
  int8 = 0x18,
  int16 = 0x19,
  int32 = 0x1a,
  int64 = 0x1b,
  bool_ = 0x20,
};

template <typename T> struct get_type_id {
  static_assert(sizeof(T) == -1, "unsupported type");
};

template <> struct get_type_id<uint8_t> {
  static constexpr type_id_t value = uint8;
};

template <> struct get_type_id<uint16_t> {
  static constexpr type_id_t value = uint16;
};

template <> struct get_type_id<uint32_t> {
  static constexpr type_id_t value = uint32;
};

template <> struct get_type_id<uint64_t> {
  static constexpr type_id_t value = uint64;
};

template <> struct get_type_id<int8_t> {
  static constexpr type_id_t value = int8;
};

template <> struct get_type_id<int16_t> {
  static constexpr type_id_t value = int16;
};

template <> struct get_type_id<int32_t> {
  static constexpr type_id_t value = int32;
};

template <> struct get_type_id<int64_t> {
  static constexpr type_id_t value = int64;
};

template <> struct get_type_id<bool> {
  static constexpr type_id_t value = bool_;
};

template <typename T> constexpr type_id_t type_id = get_type_id<T>::value;

template <typename T, typename... Ts>
constexpr bool is_any = (std::is_same_v<T, Ts> || ...);

template <typename T>
constexpr bool is_uint = is_any<T, uint8_t, uint16_t, uint32_t, uint64_t>;

template <typename T>
constexpr bool is_int = is_any<T, int8_t, int16_t, int32_t, int64_t>;

using bytes_t = std::vector<uint8_t>;

template <typename T, std::enable_if_t<is_uint<T> || is_int<T>, bool> = true>
inline void pack(bytes_t &bytes, T value) {
  bytes.push_back(type_id<T>);
  for (auto i = sizeof(T); i; --i) {
    bytes.push_back(static_cast<uint8_t>((value >> (8 * (i - 1))) & 0xff));
  }
}

inline void pack(bytes_t &bytes, bool value) {
  bytes.push_back(type_id<bool>);
  bytes.push_back(static_cast<uint8_t>(value));
}

template <typename T> bytes_t pack(const T &value) {
  bytes_t bytes;
  pack(bytes, value);
  return bytes;
}
}; // namespace pack

#include <cstdio>
int main() {
  const auto b = pack::pack(true);
  for (const auto &v : b) {
    printf("%02x ", v);
  }
  printf("\n");
}
