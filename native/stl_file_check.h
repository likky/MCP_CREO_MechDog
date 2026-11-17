// BUG-130: SDK-independent ASCII STL acceptance.
//
// The old export path trusted the Triangulation API's nested pointers and
// wrote whatever it found. This header validates the exported file itself:
// syntax, finite coordinates, facet budget and byte budget. It never loads the
// whole file, never calls Toolkit and never connects to Creo.
#pragma once

#include <array>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct StlOutputLimits {
    std::uint64_t max_facets = 2000000;
    std::uint64_t max_bytes = 512ull * 1024 * 1024;
};

struct StlFileStats {
    std::uint64_t facet_count = 0;
    std::uint64_t bytes = 0;
    std::array<double, 3> min = {std::numeric_limits<double>::infinity(),
                                 std::numeric_limits<double>::infinity(),
                                 std::numeric_limits<double>::infinity()};
    std::array<double, 3> max = {-std::numeric_limits<double>::infinity(),
                                 -std::numeric_limits<double>::infinity(),
                                 -std::numeric_limits<double>::infinity()};
};

class StlFileError : public std::runtime_error {
  public:
    enum class Reason {
        open_failed,
        empty,
        too_many_bytes,
        too_many_facets,
        truncated,
        malformed,
        non_finite,
    };
    StlFileError(Reason reason, const std::string &message)
        : std::runtime_error(message), reason(reason) {
    }
    Reason reason;
};

namespace stl_file_check_detail {

inline std::vector<std::string> tokens(const std::string &line) {
    std::istringstream stream(line);
    std::vector<std::string> result;
    std::string token;
    while (stream >> token)
        result.push_back(token);
    return result;
}

inline std::string lowered(std::string value) {
    for (char &c : value)
        if (c >= 'A' && c <= 'Z')
            c = static_cast<char>(c - 'A' + 'a');
    return value;
}

inline double coordinate(const std::string &token, std::uint64_t line_number) {
    const char *begin = token.c_str();
    char *end = nullptr;
    const double value = std::strtod(begin, &end);
    if (end == begin || *end != '\0' || !std::isfinite(value))
        throw StlFileError(StlFileError::Reason::non_finite,
                           "non-finite vertex coordinate at line " + std::to_string(line_number) +
                               ": " + token);
    return value;
}

inline void observe_bounds(StlFileStats &stats, const double vertex[3]) {
    for (int axis = 0; axis < 3; ++axis) {
        if (vertex[axis] < stats.min[axis])
            stats.min[axis] = vertex[axis];
        if (vertex[axis] > stats.max[axis])
            stats.max[axis] = vertex[axis];
    }
}

} // namespace stl_file_check_detail

// Streams a complete ASCII STL and reports facet count, bytes and bounds.
// Every malformed/truncated/non-finite/over-budget file throws StlFileError
// with a distinct reason; a syntactically valid but facet-less file is
// rejected as empty instead of being reported as a successful export.
inline StlFileStats validate_ascii_stl(const std::filesystem::path &file,
                                       const StlOutputLimits &limits = {}) {
    using namespace stl_file_check_detail;
    std::error_code size_error;
    std::uintmax_t size = std::filesystem::file_size(file, size_error);
    if (size_error)
        throw StlFileError(StlFileError::Reason::open_failed,
                           "cannot read STL file size: " + size_error.message());
    if (size == 0)
        throw StlFileError(StlFileError::Reason::empty, "STL file is empty");
    if (size > limits.max_bytes)
        throw StlFileError(StlFileError::Reason::too_many_bytes,
                           "STL file exceeds the byte budget: " + std::to_string(size));

    std::ifstream input(file, std::ios::binary);
    if (!input)
        throw StlFileError(StlFileError::Reason::open_failed, "cannot open STL file");

    enum class Phase {
        Header,
        Facet,
        OuterLoop,
        Vertex,
        EndLoop,
        EndFacet,
        Done
    };
    Phase phase = Phase::Header;
    int vertices = 0;
    std::uint64_t line_number = 0;
    StlFileStats stats;
    stats.bytes = static_cast<std::uint64_t>(size);
    std::string line;
    while (std::getline(input, line)) {
        ++line_number;
        const std::vector<std::string> parts = tokens(line);
        if (parts.empty())
            continue;
        const std::string keyword = lowered(parts[0]);
        switch (phase) {
        case Phase::Header:
            if (keyword != "solid")
                throw StlFileError(StlFileError::Reason::malformed,
                                   "STL does not start with solid at line " +
                                       std::to_string(line_number));
            phase = Phase::Facet;
            break;
        case Phase::Facet:
            if (keyword == "endsolid") {
                phase = Phase::Done;
                break;
            }
            if (keyword != "facet")
                throw StlFileError(StlFileError::Reason::malformed,
                                   "expected facet at line " + std::to_string(line_number));
            phase = Phase::OuterLoop;
            break;
        case Phase::OuterLoop:
            if (parts.size() < 2 || keyword != "outer" || lowered(parts[1]) != "loop")
                throw StlFileError(StlFileError::Reason::malformed,
                                   "expected outer loop at line " + std::to_string(line_number));
            vertices = 0;
            phase = Phase::Vertex;
            break;
        case Phase::Vertex:
            if (keyword != "vertex" || parts.size() < 4)
                throw StlFileError(StlFileError::Reason::truncated,
                                   "facet has fewer than three vertices before line " +
                                       std::to_string(line_number));
            {
                double vertex[3];
                for (int axis = 0; axis < 3; ++axis)
                    vertex[axis] = coordinate(parts[axis + 1], line_number);
                observe_bounds(stats, vertex);
            }
            if (++vertices == 3)
                phase = Phase::EndLoop;
            break;
        case Phase::EndLoop:
            if (keyword != "endloop")
                throw StlFileError(StlFileError::Reason::truncated,
                                   "missing endloop at line " + std::to_string(line_number));
            phase = Phase::EndFacet;
            break;
        case Phase::EndFacet:
            if (keyword != "endfacet")
                throw StlFileError(StlFileError::Reason::truncated,
                                   "missing endfacet at line " + std::to_string(line_number));
            if (++stats.facet_count > limits.max_facets)
                throw StlFileError(StlFileError::Reason::too_many_facets,
                                   "STL exceeds the facet budget: " +
                                       std::to_string(stats.facet_count));
            phase = Phase::Facet;
            break;
        case Phase::Done:
            throw StlFileError(StlFileError::Reason::malformed,
                               "content after endsolid at line " + std::to_string(line_number));
        }
    }
    if (input.bad())
        throw StlFileError(StlFileError::Reason::open_failed, "error while reading STL file");
    if (phase != Phase::Done)
        throw StlFileError(StlFileError::Reason::truncated,
                           "STL ended before endsolid at line " + std::to_string(line_number));
    if (stats.facet_count == 0)
        throw StlFileError(StlFileError::Reason::empty, "STL contains no facets");
    return stats;
}
