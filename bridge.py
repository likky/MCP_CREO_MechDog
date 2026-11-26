"""Keep the existing build and detached-runner commands available."""

import importlib
import sys

from creo_mechdog.paths import require_entry_checkout

require_entry_checkout(__file__)
_implementation = importlib.import_module("creo_mechdog.bridge")

if __name__ == "__main__":
    _implementation.main()
else:
    sys.modules[__name__] = _implementation
