"""
Entry point module for web2json package.
Allows running the package as a module: python -m web2json
"""
import sys
import runpy

if __name__ == "__main__":
    # Instead of importing directly, use runpy to execute cli.py
    sys.exit(runpy.run_module("web2json.cli", run_name="__main__"))