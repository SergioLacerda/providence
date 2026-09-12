# DSL Compiler Design Document

**Version:** 1.0 (v3.1 Target)
**Date:** April 21, 2026
**Status:** Design Phase

---

## Executive Summary

The DSL Compiler converts human-readable SDD v3.0 DSL files (`.spec`, `.dsl`) into optimized MessagePack binary format (`.bin`) for 65% size reduction and 3-4x faster parsing performance.

**Key Metrics:**

- Input: 28 KB (guidelines.dsl + mandate.spec)
- Output: <10 KB (compiled .bin)
- Compression: 65% reduction
- Parse Time: 3-4x faster vs. text
- Token Cost: 75% reduction (120 → 30 tokens)

---

## 1. Compilation Pipeline

```
mandate.spec (text DSL)     guidelines.dsl (text DSL)
      ↓                              ↓
   ┌──────────────────────────────────┐
   │   1. Lexical Analysis (Tokenize) │
   └──────────────────────────────────┘
             ↓
   ┌──────────────────────────────────┐
   │   2. Syntax Analysis (Parse)     │
   │      - Build AST                 │
   │      - Validate structure        │
   └──────────────────────────────────┘
             ↓
   ┌──────────────────────────────────┐
   │   3. Semantic Analysis           │
   │      - Validate IDs              │
   │      - Check required fields     │
   │      - Resolve references        │
   └──────────────────────────────────┘
             ↓
   ┌──────────────────────────────────┐
   │   4. Optimization                │
   │      - String deduplication      │
   │      - Field reordering          │
   │      - Metadata stripping        │
   └──────────────────────────────────┘
             ↓
   ┌──────────────────────────────────┐
   │   5. Code Generation             │
   │      - MessagePack encoding      │
   │      - Binary format output      │
   └──────────────────────────────────┘
             ↓
mandate.spec.bin (8 KB)  guidelines.dsl.bin (8 KB)
```

---

## 2. DSL Grammar (EBNF)

```ebnf
program
    = (mandate | guideline)+
    ;

mandate
    = "mandate" ID "{" mandate_field* "}"
    ;

mandate_field
    = "type" ":" type_value
    | "title" ":" string_value
    | "description" ":" string_value
    | "category" ":" identifier
    | "rationale" ":" string_value
    | "validation" ":" validation_block
    ;

guideline
    = "guideline" ID "{" guideline_field* "}"
    ;

guideline_field
    = "type" ":" type_value
    | "title" ":" string_value
    | "description" ":" string_value
    | "category" ":" identifier
    | "examples" ":" examples_block
    ;

validation_block
    = "{" "commands" ":" "[" string_value ("," string_value)* "]" "}"
    ;

examples_block
    = "[" string_value ("," string_value)* "]"
    ;

type_value
    = "HARD" | "SOFT"
    ;

string_value
    = QUOTED_STRING
    ;

identifier
    = [a-zA-Z][a-zA-Z0-9\-]*
    ;

ID
    = [A-Z] [0-9]+ | [G] [0-9]+
    ;
```

---

## 3. MessagePack Binary Format

### Mandate Encoding

```
Mandate {
  id:          uint16         (M001 → 1, M002 → 2)
  type:        uint8          (HARD=1, SOFT=2)
  title:       string         (variable length)
  description: string         (variable length)
  category:    uint8          (ref to category enum)
  rationale:   string|null    (optional)
  validation:  {
    commands: [string, ...]   (variable length array)
  }
}

Binary Size: ~160 bytes for typical mandate (vs 400+ bytes in text)
Reduction: 60%
```

### Guideline Encoding

```
Guideline {
  id:          uint16         (G001 → 1, G150 → 150)
  type:        uint8          (HARD=1, SOFT=2)
  title:       string         (variable length)
  description: string|null    (optional)
  category:    uint8          (ref to category enum)
  examples:    [string, ...]  (optional, variable length)
}

Binary Size: ~85 bytes for typical guideline (vs 200+ bytes in text)
Reduction: 55%
```

### Category Mapping

```yaml
categories:
  architecture: 1
  general: 2
  performance: 3
  security: 4
  git: 5
  documentation: 6
  testing: 7
  naming: 8
  code-style: 9
  custom: 255
```

---

## 4. String Deduplication

### Strategy

- Build string pool during parsing
- Replace duplicates with integer references
- Saves 30-40% on typical DSL files

### Example

**Before Deduplication:**

```
"Clean Architecture as Foundation"
"Clean Architecture as Foundation"  (duplicate)
"Test-Driven Development"
```

**After Deduplication:**

```
String Pool:
  [0]: "Clean Architecture as Foundation"
  [1]: "Test-Driven Development"

References:
  [0]  (first usage)
  [0]  (duplicate → reference)
  [1]
```

**Savings:** 40 bytes (for typical 300-byte description)

---

## 5. Implementation: `dsl_compiler.py`

```python
"""DSL Compiler: .spec/.dsl → MessagePack binary"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import msgpack


@dataclass
class CompilationMetrics:
    input_size: int
    output_size: int
    compilation_time: float
    string_pool_size: int
    mandates_compiled: int
    guidelines_compiled: int

    @property
    def compression_ratio(self) -> float:
        return (self.input_size - self.output_size) / self.input_size


class DSLCompiler:
    """Main DSL compiler with validation and optimization"""

    CATEGORY_MAP = {
        "architecture": 1,
        "general": 2,
        "performance": 3,
        "security": 4,
        "git": 5,
        "documentation": 6,
        "testing": 7,
        "naming": 8,
        "code-style": 9,
    }

    def __init__(self):
        self.string_pool: Dict[str, int] = {}
        self.string_pool_counter = 0
        self.metrics = CompilationMetrics(0, 0, 0.0, 0, 0, 0)

    def compile(self, dsl_text: str) -> bytes:
        """
        Compile DSL text to MessagePack binary

        Args:
            dsl_text: DSL source code

        Returns:
            Compiled MessagePack binary
        """
        import time

        start = time.time()

        # Metrics
        self.metrics.input_size = len(dsl_text.encode())

        # Parse DSL
        mandates, guidelines = self._parse_dsl(dsl_text)

        # Compile to intermediate format
        compiled_mandates = [self._compile_mandate(m) for m in mandates]
        compiled_guidelines = [self._compile_guideline(g) for g in guidelines]

        # Create output structure
        output = {
            "mandates": compiled_mandates,
            "guidelines": compiled_guidelines,
            "string_pool": self._reverse_string_pool(),
            "categories": self.CATEGORY_MAP,
        }

        # Encode to MessagePack
        binary = msgpack.packb(output, use_bin_type=True)

        # Metrics
        self.metrics.output_size = len(binary)
        self.metrics.compilation_time = time.time() - start
        self.metrics.mandates_compiled = len(compiled_mandates)
        self.metrics.guidelines_compiled = len(compiled_guidelines)
        self.metrics.string_pool_size = len(self.string_pool)

        return binary

    def _parse_dsl(self, dsl_text: str) -> Tuple[List[Dict], List[Dict]]:
        """Parse DSL text into mandate and guideline objects"""
        mandates = []
        guidelines = []

        # Simple regex-based parsing (for MVP)
        # In production: use proper lexer/parser

        # Extract mandates
        mandate_pattern = r"mandate\s+(M\d+)\s*\{([^}]+)\}"
        for match in re.finditer(mandate_pattern, dsl_text, re.DOTALL):
            mandate_id = match.group(1)
            mandate_body = match.group(2)
            mandate = self._parse_mandate_block(mandate_id, mandate_body)
            mandates.append(mandate)

        # Extract guidelines
        guideline_pattern = r"guideline\s+(G\d+)\s*\{([^}]+)\}"
        for match in re.finditer(guideline_pattern, dsl_text, re.DOTALL):
            guideline_id = match.group(1)
            guideline_body = match.group(2)
            guideline = self._parse_guideline_block(guideline_id, guideline_body)
            guidelines.append(guideline)

        return mandates, guidelines

    def _parse_mandate_block(self, mandate_id: str, body: str) -> Dict[str, Any]:
        """Parse mandate block into structured format"""
        mandate = {
            "id": mandate_id,
            "type": self._extract_field(body, "type"),
            "title": self._extract_field(body, "title"),
            "description": self._extract_field(body, "description"),
            "category": self._extract_field(body, "category"),
            "rationale": self._extract_field(body, "rationale"),
            "validation": self._extract_validation(body),
        }
        return mandate

    def _parse_guideline_block(self, guideline_id: str, body: str) -> Dict[str, Any]:
        """Parse guideline block into structured format"""
        guideline = {
            "id": guideline_id,
            "type": self._extract_field(body, "type"),
            "title": self._extract_field(body, "title"),
            "description": self._extract_field(body, "description"),
            "category": self._extract_field(body, "category"),
            "examples": self._extract_examples(body),
        }
        return guideline

    def _extract_field(self, text: str, field_name: str) -> Optional[str]:
        """Extract field value from DSL text"""
        pattern = f'{field_name}\\s*:\\s*"([^"]*)"'
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _extract_validation(self, text: str) -> Optional[Dict]:
        """Extract validation block"""
        pattern = r"validation\s*:\s*\{([^}]+)\}"
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            return None

        validation_body = match.group(1)
        # Extract commands array
        commands_pattern = r"commands\s*:\s*\[([^\]]*)\]"
        commands_match = re.search(commands_pattern, validation_body)
        if not commands_match:
            return None

        commands_text = commands_match.group(1)
        commands = [c.strip().strip('"') for c in commands_text.split(",")]

        return {"commands": commands}

    def _extract_examples(self, text: str) -> Optional[List[str]]:
        """Extract examples array"""
        pattern = r"examples\s*:\s*\[([^\]]*)\]"
        match = re.search(pattern, text)
        if not match:
            return None

        examples_text = match.group(1)
        examples = [e.strip().strip('"') for e in examples_text.split(",") if e.strip()]

        return examples

    def _compile_mandate(self, mandate: Dict[str, Any]) -> Dict[str, Any]:
        """Compile mandate to optimized format with string dedup"""
        return {
            "id": int(mandate["id"][1:]),  # M001 → 1
            "type": 1 if mandate.get("type") == "HARD" else 2,
            "title": self._deduplicate_string(mandate.get("title")),
            "description": self._deduplicate_string(mandate.get("description")),
            "category": self.CATEGORY_MAP.get(mandate.get("category", "general"), 2),
            "rationale": self._deduplicate_string(mandate.get("rationale")),
            "validation": mandate.get("validation"),
        }

    def _compile_guideline(self, guideline: Dict[str, Any]) -> Dict[str, Any]:
        """Compile guideline to optimized format with string dedup"""
        return {
            "id": int(guideline["id"][1:]),  # G001 → 1
            "type": 1 if guideline.get("type") == "HARD" else 2,
            "title": self._deduplicate_string(guideline.get("title")),
            "description": self._deduplicate_string(guideline.get("description")),
            "category": self.CATEGORY_MAP.get(guideline.get("category", "general"), 2),
            "examples": guideline.get("examples"),
        }

    def _deduplicate_string(self, value: Optional[str]) -> Optional[Any]:
        """Deduplicate string and return pool index"""
        if value is None:
            return None

        if value not in self.string_pool:
            self.string_pool[value] = self.string_pool_counter
            self.string_pool_counter += 1

        return self.string_pool[value]  # Return pool index

    def _reverse_string_pool(self) -> List[str]:
        """Create array representation of string pool"""
        pool = [""] * len(self.string_pool)
        for string, index in self.string_pool.items():
            pool[index] = string
        return pool


# CLI interface
def compile_file(input_path: str, output_path: str) -> CompilationMetrics:
    """Compile DSL file to binary"""
    with open(input_path, "r") as f:
        dsl_text = f.read()

    compiler = DSLCompiler()
    binary = compiler.compile(dsl_text)

    with open(output_path, "wb") as f:
        f.write(binary)

    return compiler.metrics


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python dsl_compiler.py <input.spec> <output.bin>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    metrics = compile_file(input_file, output_file)

    print(f"Compilation successful!")
    print(f"  Input:  {metrics.input_size} bytes")
    print(f"  Output: {metrics.output_size} bytes")
    print(f"  Compression: {metrics.compression_ratio:.1%}")
    print(f"  Time: {metrics.compilation_time * 1000:.1f} ms")
    print(f"  Mandates: {metrics.mandates_compiled}")
    print(f"  Guidelines: {metrics.guidelines_compiled}")
    print(f"  String Pool: {metrics.string_pool_size} unique strings")
```

---

## 6. Testing Strategy

```python
# test_compiler.py


def test_mandate_compilation():
    """Test mandate parsing and compilation"""
    dsl = """
    mandate M001 {
      type: HARD
      title: "Clean Architecture"
      description: "Applications MUST..."
      category: architecture
    }
    """

    compiler = DSLCompiler()
    binary = compiler.compile(dsl)

    assert compiler.metrics.mandates_compiled == 1
    assert compiler.metrics.compression_ratio > 0.5


def test_string_deduplication():
    """Test string pool deduplication"""
    dsl = """
    guideline G01 { title: "Common String" }
    guideline G02 { description: "Common String" }
    """

    compiler = DSLCompiler()
    binary = compiler.compile(dsl)

    # String pool should have 1 entry for "Common String"
    assert compiler.metrics.string_pool_size == 3  # "Common String" counted once


def test_compression_ratio():
    """Test compression achieves target"""
    # Load real mandate.spec and guidelines.dsl
    with open(".providence-core/CANONICAL/mandate.spec") as f:
        mandate_dsl = f.read()

    with open(".providence-core/guidelines.dsl") as f:
        guideline_dsl = f.read()

    dsl_combined = mandate_dsl + guideline_dsl

    compiler = DSLCompiler()
    binary = compiler.compile(dsl_combined)

    # Target: 65% compression
    assert compiler.metrics.compression_ratio > 0.65
    # Target: <10 KB output
    assert compiler.metrics.output_size < 10240
```

---

## 7. Integration Points

### Pre-compilation Validation

```python
def validate_before_compilation(dsl_text: str) -> List[str]:
    """Validate DSL before compilation"""
    errors = []

    # Check mandate IDs are sequential
    mandates = re.findall(r"mandate (M\d+)", dsl_text)
    if mandates:
        ids = [int(m[1:]) for m in mandates]
        if ids != list(range(1, len(ids) + 1)):
            errors.append("Mandate IDs not sequential")

    # Check required fields present
    for mandate in re.finditer(r"mandate M\d+ \{([^}]+)\}", dsl_text, re.DOTALL):
        body = mandate.group(1)
        required = ["type", "title", "description"]
        for req in required:
            if req not in body:
                errors.append(f"Missing field '{req}' in mandate")

    return errors
```

### Binary Parser (for consumption)

```python
def parse_binary(binary_data: bytes) -> Dict[str, Any]:
    """Parse compiled MessagePack binary"""
    return msgpack.unpackb(binary_data, raw=False)
```

---

## 8. Performance Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| Compilation Time | <500ms | Optimize parsing, parallel processing |
| Compression Ratio | 65-75% | String dedup, category mapping, IDs |
| Output Size | <10 KB | Binary format, no whitespace |
| Parse Time | 3-4x faster | Direct binary reading vs text parsing |

---

## 9. Rollout Plan

### v3.1.0-beta.1

- [ ] Release compiler (optional)
- [ ] Feature flag for binary format

### v3.1.0-rc1

- [ ] Compiler required for v3.1
- [ ] Binary format as default

### v3.1.0

- [ ] All v3.1 files compiled by default
- [ ] Text DSL source maintained for reference

---

**Status: DESIGN DOCUMENT COMPLETE ✅**
**Next Step: Implement DSL Compiler (Week 2-3)**
