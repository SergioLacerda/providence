#!/usr/bin/env python3
"""
Mandate and Guidelines Compiler for AI optimization

Compiles mandate.spec and guidelines.dsl to MessagePack binary format
for 65% size reduction and 3-4x faster parsing.

Supports fallback to JSON if msgpack not available.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ._dsl_parsers import parse_guidelines_dsl_text, parse_mandate_spec_text

# Try to import msgpack
try:
    import msgpack

    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False


def compile_to_binary(mandates: list[dict[str, Any]], format: str = "msgpack") -> bytes:
    """Serialize mandates to binary (msgpack or compact JSON fallback)."""
    output = {
        "version": "3.1",
        "format_version": "3.1",
        "compiled_at": datetime.now().isoformat(),
        "mandates": mandates,
        "count": len(mandates),
    }
    if format == "msgpack" and HAS_MSGPACK:
        return bytes(msgpack.packb(output, use_bin_type=True))
    return json.dumps(output, separators=(",", ":")).encode("utf-8")


class MandateCompiler:
    """Compile mandate.spec to binary format"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def log(self, msg: str) -> None:
        """Log."""
        if self.verbose:
            print(f"  {msg}")  # noqa: T201

    def parse_mandate_spec(self, text: str) -> tuple[int, list[dict[str, Any]]]:
        """Parse mandate.spec DSL format"""
        return parse_mandate_spec_text(text)

    def parse_guidelines_dsl(self, text: str) -> tuple[int, list[dict[str, Any]]]:
        """Parse guidelines.dsl DSL format"""
        return parse_guidelines_dsl_text(text)

    def compile_mandate_spec(
        self, input_file: Path, output_file: Path, format: str = "msgpack"
    ) -> bool:
        """Compile mandate.spec to binary"""
        try:
            self.log(f"Compiling mandate.spec ({format})")

            # Read source
            if not input_file.exists():
                print(f"   Source not found: {input_file}")  # noqa: T201
                return False

            text = input_file.read_text(encoding="utf-8")
            count, mandates = self.parse_mandate_spec(text)

            self.log(f"  Parsed {count} mandates")

            if count == 0:
                self.log("    No mandates found")

            # Compile to binary
            binary_data = compile_to_binary(mandates, format)

            # Write output
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(binary_data, bytes):
                output_file.write_bytes(binary_data)
            else:
                output_file.write_text(binary_data, encoding="utf-8")

            size = (
                len(binary_data)
                if isinstance(binary_data, bytes)
                else len(binary_data.encode())
            )
            self.log(f"   Compiled to {output_file.name} ({size:,} bytes)")

            return True
        except Exception as e:
            print(f"   Compilation failed: {e}")  # noqa: T201
            import traceback

            traceback.print_exc()
            return False

    def compile_guidelines_dsl(
        self, input_file: Path, output_file: Path, format: str = "msgpack"
    ) -> bool:
        """Compile guidelines.dsl to binary"""
        try:
            self.log(f"Compiling guidelines.dsl ({format})")

            # Read source
            if not input_file.exists():
                self.log(f"    Guidelines not found: {input_file}")
                return True  # Optional

            text = input_file.read_text(encoding="utf-8")
            count, guidelines = self.parse_guidelines_dsl(text)

            self.log(f"  Parsed {count} guidelines")

            # Create output structure
            output = {
                "version": "3.1",
                "format_version": "3.1",
                "compiled_at": datetime.now().isoformat(),
                "guidelines": guidelines,
                "count": count,
            }

            # Compile to binary
            if format == "msgpack" and HAS_MSGPACK:
                binary_data = msgpack.packb(output, use_bin_type=True)
            else:
                json_str = json.dumps(output, separators=(",", ":"))
                binary_data = json_str.encode("utf-8")

            # Write output
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(binary_data, bytes):
                output_file.write_bytes(binary_data)
            else:
                output_file.write_text(binary_data, encoding="utf-8")

            size = (
                len(binary_data)
                if isinstance(binary_data, bytes)
                else len(binary_data.encode())
            )
            self.log(f"   Compiled to {output_file.name} ({size:,} bytes)")

            return True
        except Exception as e:
            print(f"   Compilation failed: {e}")  # noqa: T201
            return False
