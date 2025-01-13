#include <cassert>

#include "pack.h"

using namespace pack;

template <typename T> void test(const T &value) {
  printf("input: %s\n", fmt::repr(value).c_str());

  const auto packed = pack::pack(value);
  printf("packed:\n");
  packed.dump();

  try {
    const auto unpacked = pack::unpack_one<T>(packed);
    printf("unpacked: %s\n", fmt::repr(unpacked).c_str());
    assert(value == unpacked);
  } catch (const std::runtime_error &e) {
    printf("failed to unpack: %s\n", e.what());
    assert(false);
  }
}

int main() {
  test<uint32_t>(5);

  test<std::vector<int8_t>>({-1, 1, -2, 2, -3, 3, -4, 4});

  test(std::string("hello world"));

  test<std::optional<uint32_t>>(std::nullopt);

  test<std::tuple<std::vector<int8_t>, std::optional<bool>, std::string,
                  uint32_t>>({{-1, -2, 3, 4}, std::nullopt, "hi", 12});

  return 0;
}
