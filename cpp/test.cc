#include <cassert>

#include "../lib/cpp_utils/fmt/fmt.h"
#include "pack.h"

using namespace fmt;
using namespace pack;
using namespace std;

template <typename T> void test(const T &value) {
  printf("input: %s\n", repr(value).c_str());

  const auto packed = pack::pack(value);
  printf("packed:\n");
  packed.dump();

  try {
    const auto unpacked = pack::unpack_one<T>(packed);
    printf("unpacked: %s\n", repr(unpacked).c_str());
    assert(value == unpacked);
  } catch (const runtime_error &e) {
    printf("failed to unpack: %s\n", e.what());
    assert(false);
  }
}

int main() {
  test<uint32_t>(5);

  test<vector<int8_t>>({-1, 1, -2, 2, -3, 3, -4, 4});

  test(string("hello world"));

  test<optional<uint32_t>>(nullopt);

  test<tuple<vector<int8_t>, optional<bool>, string, uint32_t>>(
      {{-1, -2, 3, 4}, nullopt, "hi", 12});

  assert(unpack_one<string>(pack::pack(string_view("12"))) == "12");

  test<variant<uint32_t, string>>("hi");

  return 0;
}
