// Measures the ASCII STL write throughput of the streamed writer and the
// fast writer, so the effect of the speed-up is a number and not a claim.
#include "stl_export.h"

#include <chrono>
#include <cstdio>
#include <random>
#include <sstream>
#include <vector>

namespace {

template <typename Stream>
bool streamed_facet(Stream &out, const std::array<double, 3> &normal,
                    const std::array<double, 3> &a, const std::array<double, 3> &b,
                    const std::array<double, 3> &c) {
    out << "facet normal " << normal[0] << ' ' << normal[1] << ' ' << normal[2]
        << "\n outer loop\n";
    for (const std::array<double, 3> *point : {&a, &b, &c})
        out << "  vertex " << (*point)[0] << ' ' << (*point)[1] << ' ' << (*point)[2] << '\n';
    out << " endloop\nendfacet\n";
    return static_cast<bool>(out);
}

} // namespace

int main() {
    const std::size_t count = 200000;
    std::mt19937_64 generator(42);
    std::uniform_real_distribution<double> distribution(-70000.0, 70000.0);
    std::vector<std::array<double, 3>> points(count * 3);
    for (std::array<double, 3> &point : points)
        for (double &value : point)
            value = distribution(generator);

    const auto measure = [&](bool fast) {
        std::ostringstream sink;
        sink.precision(12);
        const auto start = std::chrono::steady_clock::now();
        for (std::size_t index = 0; index < count; ++index) {
            const std::array<double, 3> normal = {0.0, 0.0, 1.0};
            const std::array<double, 3> &a = points[index * 3];
            const std::array<double, 3> &b = points[index * 3 + 1];
            const std::array<double, 3> &c = points[index * 3 + 2];
            if (fast)
                stl_surface_detail::write_facet(sink, normal, a, b, c);
            else
                streamed_facet(sink, normal, a, b, c);
        }
        const auto stop = std::chrono::steady_clock::now();
        const auto micros =
            std::chrono::duration_cast<std::chrono::microseconds>(stop - start).count();
        const double per_facet = static_cast<double>(micros) / static_cast<double>(count);
        std::printf("%s: %.2f us/facet, %.1f MB output\n", fast ? "fast   " : "streamed", per_facet,
                    static_cast<double>(sink.tellp()) / (1024.0 * 1024.0));
        return per_facet;
    };
    const double streamed = measure(false);
    const double fast = measure(true);
    std::printf("speedup: %.2fx\n", streamed / fast);
    return 0;
}
