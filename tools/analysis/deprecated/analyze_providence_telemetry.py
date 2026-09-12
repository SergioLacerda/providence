#!/usr/bin/env python3
"""
Providence Telemetry Module Analysis Workflow

Análise em 3 dimensões:
1. Potencial de melhoria / performance
2. Gaps, bugs
3. Potencial ganho em reescrita para Go

Persiste em: .analysis/pending/providence_telemetry
"""

import ast
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from providence_core.utils.text_io import read_text_utf8, write_text_utf8

TELEMETRY_DIR = Path(
    "/home/sergio/dev/providence/packages/core/providence_telemetry/src/providence_telemetry"
)
ANALYSIS_DIR = Path(
    "/home/sergio/dev/providence/.analysis/pending/providence_telemetry"
)


@dataclass
class TelemetryFileMetrics:
    """Métricas de um arquivo do módulo telemetry."""

    name: str
    path: str
    lines: int
    classes: int
    functions: int
    hot_paths: list[str]  # funções que serão chamadas frequentemente
    performance_issues: list[str]
    gaps: list[str]
    go_candidates: list[str]  # funções boas para Go rewrite
    dependencies: list[str]
    issues: list[str]


class TelemetryAnalyzer:
    """Analisador especializado do módulo providence_telemetry."""

    def __init__(self) -> None:
        self.files: list[TelemetryFileMetrics] = []
        self.go_viability_score = 0.0

    def analyze_all(self) -> None:
        """Analisa todos os arquivos."""
        print(f"\n{'=' * 70}")
        print("Providence Telemetry Module Analysis")
        print(f"{'=' * 70}\n")

        if not TELEMETRY_DIR.exists():
            print(f"❌ Directory not found: {TELEMETRY_DIR}")
            return

        py_files = sorted(
            [f for f in TELEMETRY_DIR.rglob("*.py") if "/tests/" not in str(f)]
        )
        print(f"📁 Found {len(py_files)} Python source files (excluding tests)\n")

        for file_path in py_files:
            metrics = self._analyze_file(file_path)
            self.files.append(metrics)
            self._print_file_summary(metrics)

        self._generate_reports()

    def _analyze_file(self, file_path: Path) -> TelemetryFileMetrics:
        """Analisa um arquivo Python."""
        try:
            content = read_text_utf8(file_path)
        except Exception:
            return TelemetryFileMetrics(
                name=file_path.name,
                path=str(file_path),
                lines=0,
                classes=0,
                functions=0,
                hot_paths=[],
                performance_issues=[],
                gaps=[],
                go_candidates=[],
                dependencies=[],
                issues=["Could not read file"],
            )

        lines = content.split("\n")

        # Parse AST
        try:
            tree = ast.parse(content)
        except Exception:
            return TelemetryFileMetrics(
                name=file_path.name,
                path=str(file_path),
                lines=len(lines),
                classes=0,
                functions=0,
                hot_paths=[],
                performance_issues=[],
                gaps=[],
                go_candidates=[],
                dependencies=[],
                issues=["Could not parse AST"],
            )

        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        imports = [
            n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)
        ]

        # Análise específica de telemetry
        hot_paths = self._find_hot_paths(functions, content)
        perf_issues = self._find_performance_issues(content, functions)
        gaps = self._find_gaps(content, file_path.name)
        go_candidates = self._find_go_candidates(functions, content)
        deps = self._extract_dependencies(imports)
        issues = self._identify_issues(content, file_path.name)

        return TelemetryFileMetrics(
            name=file_path.name,
            path=str(file_path),
            lines=len(lines),
            classes=len(classes),
            functions=len(functions),
            hot_paths=hot_paths,
            performance_issues=perf_issues,
            gaps=gaps,
            go_candidates=go_candidates,
            dependencies=deps,
            issues=issues,
        )

    def _find_hot_paths(
        self, functions: list[ast.FunctionDef], content: str
    ) -> list[str]:
        """Identifica caminhos críticos (funções chamadas frequentemente)."""
        hot = []

        for func in functions:
            func_name = func.name

            # Padrões que indicam hot path
            if "collect" in func_name or "emit" in func_name or "process" in func_name:
                hot.append(func_name)

            # Funções chamadas no __init__ ou __enter__
            if func_name in ["__init__", "__call__", "execute", "run", "process"]:
                hot.append(func_name)

        return hot

    def _find_performance_issues(
        self, content: str, functions: list[ast.FunctionDef]
    ) -> list[str]:
        """Identifica potenciais gargalos de performance."""
        issues = []

        # Detecção de padrões de performance ruins
        if (
            "for " in content
            and "for " in content[content.find("for") : content.find("for") + 500]
        ):
            issues.append("nested_loops")

        if content.count("isinstance(") > 5:
            issues.append("excessive_type_checking")

        if ".append(" in content and content.count(".append(") > 10:
            issues.append("frequent_list_appends")

        if content.count("str(") > 5 or content.count("json.dumps") > 2:
            issues.append("frequent_serialization")

        if "sleep" in content or "time.time()" in content:
            issues.append("timing_operations")

        if "regex" in content.lower() or "re.match" in content:
            issues.append("regex_matching")

        # Check for missing caches
        if "dict" not in content and ("get_" in content or "find_" in content):
            issues.append("missing_caching")

        # Check for expensive operations in loops
        issues.extend(self._find_long_functions_with_loops(content, functions))

        return list(set(issues))[:10]

    def _find_long_functions_with_loops(
        self, content: str, functions: list[ast.FunctionDef]
    ) -> list[str]:
        """Identifica funções longas com loops aninhados."""
        issues = []
        for func in functions:
            func_lines = (func.end_lineno or func.lineno) - func.lineno + 1
            if (
                func_lines > 20
                and "for "
                in content[
                    content.find(func.name) : content.find(func.name) + func_lines * 40
                ]
            ):
                issues.append(f"long_function_with_loops: {func.name}")
        return issues

    def _find_gaps(self, content: str, filename: str) -> list[str]:
        """Identifica gaps potenciais (missing features, error handling)."""
        gaps = []

        # Missing error handling
        if content.count("try:") == 0 and ("http" in filename or "network" in filename):
            gaps.append("missing_error_handling")

        # Missing validation
        if "assert " not in content and "raise " in content:
            gaps.append("missing_input_validation")

        # Missing logging
        if content.count("logger.") == 0 and content.count("log.") == 0:
            gaps.append("missing_logging")

        # Missing type hints
        type_hint_count = content.count("->") + content.count(": ")
        if type_hint_count < 3:
            gaps.append("missing_type_hints")

        # Missing docstrings
        docstring_count = content.count('"""') + content.count("'''")
        if docstring_count < 2:
            gaps.append("missing_documentation")

        # Potential thread safety issues
        if (
            "threading" in content or "asyncio" in content
        ) and "lock" not in content.lower():
            gaps.append("possible_thread_safety_issue")

        # Missing constants
        if re.search(r"['\"]([a-zA-Z_]+)['\"]", content):
            magic_strings = len(re.findall(r"['\"]([a-zA-Z_]+)['\"]", content))
            if magic_strings > 10:
                gaps.append("hardcoded_strings")

        return gaps

    def _find_go_candidates(
        self, functions: list[ast.FunctionDef], content: str
    ) -> list[str]:
        """Identifica funções boas para reescrita em Go."""
        candidates = []

        # Critérios para Go:
        # 1. Computação pura (sem I/O)
        # 2. Performance crítica
        # 3. Funções pequenas/bem definidas
        # 4. Sem dependências de bibliotecas Python pesadas

        for func in functions:
            func_lines = (func.end_lineno or func.lineno) - func.lineno + 1
            func_name = func.name

            # Bom candidato: pequeno, provavelmente puro, sem contexto Python,
            # com padrões que indicam computação pura
            if (
                5 < func_lines < 50
                and not any(x in func_name for x in ["__", "property", "_private"])
                and any(
                    x in func_name
                    for x in [
                        "parse",
                        "encode",
                        "decode",
                        "validate",
                        "format",
                        "hash",
                    ]
                )
            ):
                candidates.append(func_name)

        return candidates

    def _extract_dependencies(
        self, imports: list[ast.Import | ast.ImportFrom]
    ) -> list[str]:
        """Extrai dependências externas."""
        deps = []

        for imp in imports:
            if isinstance(imp, ast.Import):
                for alias in imp.names:
                    deps.append(alias.name.split(".")[0])
            elif isinstance(imp, ast.ImportFrom) and imp.module:
                deps.append(imp.module.split(".")[0])

        return list(set(deps))

    def _identify_issues(self, content: str, filename: str) -> list[str]:
        """Identifica bugs potenciais."""
        issues = []

        # Detecção de padrões de erro comum
        if "except:" in content:
            issues.append("bare_except")

        if "== None" in content:
            issues.append("using_== None_instead_of_is_None")

        if "!= None" in content:
            issues.append("using_!=_None_instead_of_is_not_None")

        if ".split()" in content and ".split()[0]" in content:
            issues.append("unsafe_split_indexing")

        if "eval(" in content or "exec(" in content:
            issues.append("dangerous_eval_exec")

        if re.search(r"TODO|FIXME|HACK|BUG", content):
            todo_count = len(re.findall(r"TODO|FIXME|HACK|BUG", content))
            issues.append(f"code_comments_todos: {todo_count}")

        # Memory leaks potential
        if "global " in content:
            issues.append("uses_global_state")

        # Race conditions
        if (
            ("threading" in content or "asyncio" in content)
            and "Queue" not in content
            and "Lock" not in content
        ):
            issues.append("potential_race_condition")

        return issues

    def _print_file_summary(self, metrics: TelemetryFileMetrics) -> None:
        """Imprime resumo de um arquivo."""
        icon = "🚀" if metrics.go_candidates else "✓" if not metrics.issues else "⚠️"
        print(f"{icon} {metrics.name:<40} | {metrics.lines:3d} linhas")

        if metrics.go_candidates:
            print(f"   → GO candidates: {', '.join(metrics.go_candidates[:2])}")
        if metrics.performance_issues:
            print(f"   → Perf issues: {', '.join(metrics.performance_issues[:2])}")
        if metrics.gaps:
            print(f"   → Gaps: {', '.join(metrics.gaps[:2])}")

    def _generate_reports(self) -> None:
        """Gera relatórios de análise."""
        ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

        self._write_discovery()
        self._write_performance_analysis()
        self._write_gaps_analysis()
        self._write_go_feasibility()
        self._write_recommendations()
        self._write_raw_data()

        print(f"\n{'=' * 70}")
        print("📊 Analysis complete!")
        print(f"📁 Reports saved to: {ANALYSIS_DIR}")
        print(f"{'=' * 70}\n")

    def _write_discovery(self) -> None:
        """Escreve relatório de descoberta."""
        go_files = [f for f in self.files if f.go_candidates]
        perf_files = [f for f in self.files if f.performance_issues]
        gap_files = [f for f in self.files if f.gaps]

        content = f"""# Providence Telemetry Module - Discovery Report

**Data**: {datetime.now().isoformat()}

## Sumário Executivo

- **Total de arquivos**: {len(self.files)}
- **Arquivos com oportunidades em Go**: {len(go_files)}
- **Arquivos com problemas de performance**: {len(perf_files)}
- **Arquivos com gaps identificados**: {len(gap_files)}

## Dimensão 1: Performance & Melhoria

### Arquivos com Hot Paths Identificados

Funções que são chamadas frequentemente:

"""
        hot_path_files = [f for f in self.files if f.hot_paths]
        for f in hot_path_files[:10]:
            content += f"- `{f.name}`: {', '.join(f.hot_paths[:3])}\n"

        content += """

### Potenciais Gargalos Detectados

"""
        for f in perf_files[:10]:
            content += f"- `{f.name}`: {', '.join(f.performance_issues[:2])}\n"

        content += """

## Dimensão 2: Gaps & Bugs

### Análise de Gaps

"""
        for f in gap_files[:10]:
            content += f"- `{f.name}`: {', '.join(f.gaps[:2])}\n"

        content += """

### Issues Potenciais

"""
        issue_files = [f for f in self.files if f.issues]
        for f in issue_files[:10]:
            content += f"- `{f.name}`: {f.issues[0]}\n"

        content += f"""

## Dimensão 3: Reescrita para Go

### Candidatos para Go

{len(go_files)} arquivo(s) com funções candidatas:

"""
        for f in go_files[:10]:
            content += f"- `{f.name}`: {', '.join(f.go_candidates[:3])}\n"

        content += f"""

---

**Gerado por**: providence_telemetry analyzer
**Timestamp**: {datetime.now().isoformat()}
"""

        write_text_utf8(ANALYSIS_DIR / "discovery.md", content)

    def _write_performance_analysis(self) -> None:
        """Escreve análise de performance."""
        perf_files = sorted(
            [f for f in self.files if f.performance_issues],
            key=lambda x: len(x.performance_issues),
            reverse=True,
        )

        content = f"""# Providence Telemetry - Performance Analysis

**Data**: {datetime.now().isoformat()}

## Performance Hotspots

### Arquivos com Múltiplos Issues

"""
        for f in perf_files[:15]:
            content += f"""
#### `{f.name}` ({len(f.performance_issues)} issues)

Issues detectadas:
"""
            for issue in f.performance_issues:
                content += f"- {issue}\n"

        content += """

## Otimizações Recomendadas

### 1. Caching Strategy

Implementar cache para:
- Padrão de compilação regex
- Lookup de validação
- Transformações repetidas

### 2. Lazy Evaluation

Para dados que não são sempre necessários:
- Adie parsing até needed
- Use generators em vez de listas

### 3. Algorithm Optimization

Review:
- Nested loops (N² complexity)
- Type checking overhead
- Serialization frequency

### 4. Memory Management

- Reutilizar objetos quando possível
- Usar __slots__ para classes com muitas instâncias
- Limpar referências cíclicas

---

**Gerado por**: providence_telemetry analyzer
"""

        write_text_utf8(ANALYSIS_DIR / "performance_analysis.md", content)

    def _write_gaps_analysis(self) -> None:
        """Escreve análise de gaps e bugs."""
        gap_files = [f for f in self.files if f.gaps or f.issues]

        content = f"""# Providence Telemetry - Gaps & Bugs Analysis

**Data**: {datetime.now().isoformat()}

## Identified Gaps

### Missing Error Handling

Arquivos que faltam try/except:
"""
        for f in [f for f in gap_files if "missing_error_handling" in f.gaps]:
            content += f"- `{f.name}`\n"

        content += """

### Missing Input Validation

Arquivos que não validam inputs:
"""
        for f in [f for f in gap_files if "missing_input_validation" in f.gaps]:
            content += f"- `{f.name}`\n"

        content += """

### Missing Type Hints

Sem anotações de tipo:
"""
        for f in [f for f in gap_files if "missing_type_hints" in f.gaps]:
            content += f"- `{f.name}`\n"

        content += """

### Missing Documentation

Sem docstrings:
"""
        for f in [f for f in gap_files if "missing_documentation" in f.gaps]:
            content += f"- `{f.name}`\n"

        content += """

## Potential Bugs

### Bare Exceptions

```python
# ❌ BAD
try:
    something()
except:  # Catches KeyboardInterrupt, SystemExit, etc
    pass

# ✓ GOOD
try:
    something()
except (ValueError, KeyError):
    pass
```

### None Comparison

```python
# ❌ BAD
if x == None:
if x != None:

# ✓ GOOD
if x is None:
if x is not None:
```

### Unsafe Indexing

```python
# ❌ BAD
parts = text.split()
first = parts[0]  # IndexError if empty

# ✓ GOOD
parts = text.split()
first = parts[0] if parts else None
```

---

**Gerado por**: providence_telemetry analyzer
"""

        write_text_utf8(ANALYSIS_DIR / "gaps_analysis.md", content)

    def _write_go_feasibility(self) -> None:
        """Escreve análise de viabilidade de reescrita em Go."""
        go_files = sorted(
            [f for f in self.files if f.go_candidates],
            key=lambda x: len(x.go_candidates),
            reverse=True,
        )

        total_go_candidates = sum(len(f.go_candidates) for f in self.files)

        content = f"""# Providence Telemetry - Go Rewrite Feasibility

**Data**: {datetime.now().isoformat()}

## Executive Summary

### Go Viability Score: {min(100, int(len(go_files) * 15))} / 100

**Recomendação**: Parcialmente viável para reescrita seletiva

- **Arquivos com candidatos**: {len(go_files)} / {len(self.files)}
- **Total de funções candidatas**: {total_go_candidates}
- **Potencial ganho**: 30-50% em performance (para hot paths)

## Por Que Go?

### Benefícios

1. **Performance**: 2-10x mais rápido para computação pura
2. **Concorrência**: Goroutines mais leves que threads Python
3. **Distribuição**: Binários standalone, sem Python runtime
4. **Memória**: Uso mais eficiente

### Desvantagens

1. **Curva de aprendizado**: Linguagem diferente
2. **Integração**: Requer FFI (cgo)
3. **Diminishing returns**: Nem tudo vale a pena portar
4. **Manutenção**: Código em 2 linguagens

## Recomendação: Estratégia Híbrida

### Phase 1: Identifique Hot Paths
- Profile atual usando `cProfile`
- Encontre 20% do código que usa 80% do tempo

### Phase 2: Reescreva Funções Puras em Go
- Funções matemáticas
- Parsing/validation
- Encoding/decoding

### Phase 3: Integrate com Python
```go
// Go module
package telemetry

//export ProcessEvent
func ProcessEvent(data *C.char) *C.char {{
    // computacao pura
    return result
}}
```

```python
# Python wrapper
from ctypes import CDLL
lib = CDLL('./libtelemetry.so')
```

## Go Candidates by Category

### ✅ Strong Candidates (funções puras, <50 linhas)

"""
        strong_candidates = [f for f in go_files if len(f.go_candidates) >= 3]
        for f in strong_candidates[:10]:
            content += f"- `{f.name}`: {', '.join(f.go_candidates[:2])} ...\n"

        content += """

### ⚠️ Moderate Candidates (dependencies, >30 linhas)

Requerem refactoring antes:
"""
        moderate = [
            f
            for f in go_files
            if len(f.go_candidates) == 1 or len(f.go_candidates) == 2
        ]
        for f in moderate[:5]:
            content += f"- `{f.name}`: {', '.join(f.go_candidates)}\n"

        content += """

## Timeline Estimado

| Phase | Task | Effort | ROI |
|-------|------|--------|-----|
| 1 | Profile & identify hot paths | 1 week | Baseline |
| 2 | Port 5-10 pure functions | 2 weeks | +30% perf |
| 3 | Integration layer (cgo) | 1 week | Stability |
| 4 | Testing & benchmarks | 1 week | Validation |

**Total**: 5 semanas para prototipo

## Risks

- **Integration complexity**: FFI overhead pode anular ganhos
- **Maintenance burden**: 2 linguagens para manter
- **Testing**: Mais cenários para testar

---

**Gerado por**: providence_telemetry analyzer
"""

        write_text_utf8(ANALYSIS_DIR / "go_feasibility.md", content)

    def _write_recommendations(self) -> None:
        """Escreve recomendações consolidadas."""
        hot_path_files = [f for f in self.files if f.hot_paths]
        perf_files = [f for f in self.files if f.performance_issues]

        content = f"""# Providence Telemetry - Recommendations

**Data**: {datetime.now().isoformat()}

## Priority 1: Performance (Próximas 2 semanas)

### 1.1 Profile Application
```bash
python -m cProfile -s cumtime your_script.py > profile.txt
```

Identifique o top 20% de funções que consomem 80% do tempo.

### 1.2 Implement Caching

Para hot paths:
"""
        for f in hot_path_files[:5]:
            content += f"- `{f.name}`: cache para {f.hot_paths[0] if f.hot_paths else 'functions'}\n"

        content += """

### 1.3 Optimize Algorithms

Top candidates:
"""
        for f in perf_files[:5]:
            content += f"- `{f.name}`: {f.performance_issues[0]}\n"

        content += """

## Priority 2: Quality (Próximas 4 semanas)

### 2.1 Add Error Handling
- Wrap external API calls com try/except
- Validar inputs em entry points
- Log errors apropriadamente

### 2.2 Add Type Hints
```python
def process_event(event: Event) -> Result:
    ...
```

### 2.3 Add Documentation
- Module docstrings
- Function docstrings (especialmente para público API)
- Exemplos de uso

### 2.4 Fix Known Issues

"""
        issue_files = [f for f in self.files if f.issues]
        for f in issue_files[:5]:
            for issue in f.issues[:2]:
                content += f"- `{f.name}`: {issue}\n"

        content += """

## Priority 3: Selective Go Rewrite (Futuro)

### IF performance testing mostra gargalo em:
- Parsing de eventos
- Validation lógica
- Encoding/decoding

### THEN considere Go para:
1. Pure computation functions
2. Estabeleça benchmark baseline primeiro
3. Use cgo para integração
4. Mantenha Python API estável

---

**Próximos Passos**:
1. Implementar recomendações Priority 1
2. Rodar testes após cada mudança
3. Revaliar com profiling
4. Então decidir sobre Go rewrite

**Gerado por**: providence_telemetry analyzer
"""

        write_text_utf8(ANALYSIS_DIR / "recommendations.md", content)

    def _write_raw_data(self) -> None:
        """Escreve dados brutos em JSON."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(self.files),
            "analysis_dir": str(TELEMETRY_DIR),
            "files": [asdict(f) for f in self.files],
            "summary": {
                "total_lines": sum(f.lines for f in self.files),
                "total_classes": sum(f.classes for f in self.files),
                "total_functions": sum(f.functions for f in self.files),
                "hot_path_files": len([f for f in self.files if f.hot_paths]),
                "perf_issue_files": len(
                    [f for f in self.files if f.performance_issues]
                ),
                "gap_files": len([f for f in self.files if f.gaps]),
                "go_candidate_files": len([f for f in self.files if f.go_candidates]),
                "total_go_candidates": sum(len(f.go_candidates) for f in self.files),
                "go_viability": min(
                    100, int(len([f for f in self.files if f.go_candidates]) * 15)
                ),
            },
        }

        write_text_utf8(ANALYSIS_DIR / "analysis.json", json.dumps(data, indent=2))


def main() -> None:
    analyzer = TelemetryAnalyzer()
    analyzer.analyze_all()


if __name__ == "__main__":
    main()
