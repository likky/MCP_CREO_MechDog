// BUG-130 offline ASCII STL acceptance check. No Toolkit, no Creo connection.
#include "stl_file_check.h"

#include <cassert>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <string>

namespace fs = std::filesystem;

static fs::path fixture(const fs::path &directory, const char *name, const std::string &text) {
    const fs::path file = directory / name;
    std::ofstream out(file, std::ios::binary);
    out << text;
    return file;
}

static const char *tetrahedron =
    "solid tetra\n"
    " facet normal 0 0 1\n"
    "  outer loop\n"
    "   vertex 0 0 0\n"
    "   vertex 1 0 0\n"
    "   vertex 0 1 0\n"
    "  endloop\n"
    " endfacet\n"
    " facet normal 0 1 0\n"
    "  outer loop\n"
    "   vertex 0 0 0\n"
    "   vertex 1 0 0\n"
    "   vertex 0 0 1\n"
    "  endloop\n"
    " endfacet\n"
    " facet normal 1 0 0\n"
    "  outer loop\n"
    "   vertex 0 0 0\n"
    "   vertex 0 1 0\n"
    "   vertex 0 0 1\n"
    "  endloop\n"
    " endfacet\n"
    " facet normal 1 1 1\n"
    "  outer loop\n"
    "   vertex 1 0 0\n"
    "   vertex 0 1 0\n"
    "   vertex 0 0 1\n"
    "  endloop\n"
    " endfacet\n"
    "endsolid tetra\n";

static void expect_reason(const fs::path &file, StlFileError::Reason reason) {
    try {
        validate_ascii_stl(file);
        assert(!"expected StlFileError");
    } catch (const StlFileError &error) {
        assert(error.reason == reason);
    }
}

int main() {
    const fs::path directory = fs::temp_directory_path() / "mechdog_stl_file_check";
    std::error_code ignored;
    fs::remove_all(directory, ignored);
    fs::create_directories(directory);

    const StlFileStats stats = validate_ascii_stl(fixture(directory, "tetra.stl", tetrahedron));
    assert(stats.facet_count == 4);
    assert(stats.bytes > 0);
    for (int axis = 0; axis < 3; ++axis) {
        assert(stats.min[axis] == 0.0);
        assert(stats.max[axis] == 1.0);
    }

    expect_reason(fixture(directory, "empty.stl", ""), StlFileError::Reason::empty);
    expect_reason(fixture(directory, "header.stl", "solid only\n"), StlFileError::Reason::truncated);
    expect_reason(fixture(directory, "two_vertices.stl",
                          "solid broken\n facet normal 0 0 1\n outer loop\n vertex 0 0 0\n "
                          "vertex 1 0 0\n endloop\n endfacet\nendsolid broken\n"),
                  StlFileError::Reason::truncated);
    expect_reason(fixture(directory, "no_endfacet.stl",
                          "solid broken\n facet normal 0 0 1\n outer loop\n vertex 0 0 0\n "
                          "vertex 1 0 0\n vertex 0 1 0\n endloop\nendsolid broken\n"),
                  StlFileError::Reason::truncated);
    expect_reason(fixture(directory, "nan.stl",
                          "solid bad\n facet normal 0 0 1\n outer loop\n vertex nan 0 0\n "
                          "vertex 1 0 0\n vertex 0 1 0\n endloop\n endfacet\nendsolid bad\n"),
                  StlFileError::Reason::non_finite);
    expect_reason(fixture(directory, "inf.stl",
                          "solid bad\n facet normal 0 0 1\n outer loop\n vertex inf 0 0\n "
                          "vertex 1 0 0\n vertex 0 1 0\n endloop\n endfacet\nendsolid bad\n"),
                  StlFileError::Reason::non_finite);
    expect_reason(fixture(directory, "malformed.stl",
                          "solid broken\n facet normal 0 0 1\n nonsense loop\n"),
                  StlFileError::Reason::malformed);

    StlOutputLimits facet_limits;
    facet_limits.max_facets = 3;
    try {
        validate_ascii_stl(fixture(directory, "budget.stl", tetrahedron), facet_limits);
        assert(!"expected facet budget failure");
    } catch (const StlFileError &error) {
        assert(error.reason == StlFileError::Reason::too_many_facets);
    }

    StlOutputLimits byte_limits;
    byte_limits.max_bytes = 10;
    try {
        validate_ascii_stl(fixture(directory, "bytes.stl", tetrahedron), byte_limits);
        assert(!"expected byte budget failure");
    } catch (const StlFileError &error) {
        assert(error.reason == StlFileError::Reason::too_many_bytes);
    }

    try {
        validate_ascii_stl(directory / "missing.stl");
        assert(!"expected open failure");
    } catch (const StlFileError &error) {
        assert(error.reason == StlFileError::Reason::open_failed);
    }

    fs::remove_all(directory, ignored);
    std::puts("STL_FILE_CHECK_OK cases=11; no Toolkit connection");
    return 0;
}
