"""Start the installed MCP server with python -m creo_mechdog."""

from creo_mechdog.server import main

if __name__ == "__main__":
    main(entry_file=__file__)
