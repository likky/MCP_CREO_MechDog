"""Launch the installed MCP service from its existing source checkout entry."""

import importlib
import sys

from creo_mechdog.paths import require_entry_checkout

require_entry_checkout(__file__)
_implementation = importlib.import_module("creo_mechdog.server")

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
