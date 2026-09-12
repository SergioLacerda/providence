#!/usr/bin/env python3
"""
Providence Runtime Module Analysis Workflow

Análise de três dimensões:
1. Refatoração: Classes/arquivos com >200 linhas
2. Performance: Gargalos, imports pesados, circular dependencies
3. Padronização: Constantes, variáveis, reuso de métodos

Persiste em: .analysis/pending/providence_runtime
"""

import ast
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from providence_core.utils.text_io import read_text_utf8, write_text_utf8

RUNTIME_DIR = Path(
    "/home/sergio/dev/providence/packages/core/providence_runtime/src/providence_runtime"
)
ANALYSIS_DIR = Path("/home/sergio/dev/providence/.analysis/pending/providence_runtime")


@dataclass
class FileMetrics:
    """Métricas de um arquivo Python."""

    name: str
    path: str
    lines: int
    classes: int
    functions: int
    imports: int
    heavy_imports: list[str]
    circular_deps: list[str]
    duplicate_patterns: list[str]
    hardcoded_values: list[str]
    long_functions: list[dict[str, Any]]
    issues: list[str]
    refactor_score: float  # 0-100


class RuntimeAnalyzer:
    """Analisador do módulo providence_runtime."""

    def __init__(self) -> None:
        self.files: list[FileMetrics] = []
        self.patterns: dict[str, defaultdict[str, list[Any]]] = {
            "constants": defaultdict(list),
            "imports": defaultdict(list),
            "duplicates": defaultdict(list),
        }

    def analyze_all(self) -> None:
        """Analisa todos os arquivos."""
        print(f"\n{'=' * 70}")
        print("Providence Runtime Module Analysis")
        print(f"{'=' * 70}\n")

        if not RUNTIME_DIR.exists():
            print(f"❌ Directory not found: {RUNTIME_DIR}")
            return

        py_files = sorted(RUNTIME_DIR.rglob("*.py"))
        print(f"📁 Found {len(py_files)} Python files\n")

        for file_path in py_files:
            metrics = self._analyze_file(file_path)
            self.files.append(metrics)
            self._print_file_summary(metrics)

        self._generate_reports()

    def _analyze_file(self, file_path: Path) -> FileMetrics:
        """Analisa um arquivo Python."""
        try:
            content = read_text_utf8(file_path)
        except Exception:
            return FileMetrics(
                name=file_path.name,
                path=str(file_path),
                lines=0,
                classes=0,
                functions=0,
                imports=0,
                heavy_imports=[],
                circular_deps=[],
                duplicate_patterns=[],
                hardcoded_values=[],
                long_functions=[],
                issues=["Could not read file"],
                refactor_score=0.0,
            )

        lines = content.split("\n")
        issues: list[str] = []

        # Parse AST
        try:
            tree = ast.parse(content)
        except Exception:
            return FileMetrics(
                name=file_path.name,
                path=str(file_path),
                lines=len(lines),
                classes=0,
                functions=0,
                imports=0,
                heavy_imports=[],
                circular_deps=[],
                duplicate_patterns=[],
                hardcoded_values=[],
                long_functions=[],
                issues=["Could not parse AST"],
                refactor_score=0.0,
            )

        # Contar elementos
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        imports = [
            n for n in ast.walk(tree) if isinstance(n, ast.Import | ast.ImportFrom)
        ]

        # Analisar imports pesados
        heavy_imports = self._find_heavy_imports(imports)

        # Analisar circular dependencies
        circular_deps = self._find_circular_deps(file_path, imports)

        # Analisar funções longas
        long_functions = self._find_long_functions(functions)

        # Analisar valores hardcoded
        hardcoded_values = self._find_hardcoded_values(content)

        # Analisar padrões duplicados
        duplicate_patterns = self._find_duplicate_patterns(content)

        # Calcular refactor score
        total_lines = len(lines)
        refactor_score = self._calculate_refactor_score(
            total_lines, len(classes), len(functions), len(issues), len(long_functions)
        )

        # Issues
        if total_lines > 200:
            issues.append(f"Arquivo muito longo ({total_lines} linhas)")
        if long_functions:
            issues.append(f"{len(long_functions)} função(ões) longa(s) (>30 linhas)")
        if hardcoded_values:
            issues.append(f"{len(hardcoded_values)} valor(es) hardcoded")
        if duplicate_patterns:
            issues.append("Padrões duplicados detectados")
        if heavy_imports:
            issues.append(f"Imports pesados: {len(heavy_imports)}")

        return FileMetrics(
            name=file_path.name,
            path=str(file_path),
            lines=total_lines,
            classes=len(classes),
            functions=len(functions),
            imports=len(imports),
            heavy_imports=heavy_imports,
            circular_deps=circular_deps,
            duplicate_patterns=duplicate_patterns,
            hardcoded_values=hardcoded_values,
            long_functions=long_functions,
            issues=issues,
            refactor_score=refactor_score,
        )

    def _find_heavy_imports(
        self, imports: list[ast.Import | ast.ImportFrom]
    ) -> list[str]:
        """Identifica imports pesados (ex: pandas, numpy, etc)."""
        heavy_modules = ["pandas", "numpy", "sklearn", "tensorflow", "torch", "cv2"]
        heavy = []

        for imp in imports:
            if isinstance(imp, ast.Import):
                for alias in imp.names:
                    if any(h in alias.name for h in heavy_modules):
                        heavy.append(alias.name)
            elif (
                isinstance(imp, ast.ImportFrom)
                and imp.module
                and any(h in imp.module for h in heavy_modules)
            ):
                heavy.append(imp.module)

        return list(set(heavy))

    def _find_circular_deps(
        self, file_path: Path, imports: list[ast.Import | ast.ImportFrom]
    ) -> list[str]:
        """Detecta possíveis circular dependencies."""
        circular = []
        file_name = file_path.stem

        for imp in imports:
            modules = []
            if isinstance(imp, ast.Import):
                modules = [alias.name for alias in imp.names]
            elif isinstance(imp, ast.ImportFrom) and imp.module:
                modules = [imp.module]

            # Se importa de providence_runtime, possível circular
            for mod in modules:
                if (
                    "providence_runtime" in mod
                    and mod != f"providence_runtime.{file_name}"
                ):
                    circular.append(mod)

        return circular

    def _find_long_functions(
        self, functions: list[ast.FunctionDef]
    ) -> list[dict[str, Any]]:
        """Encontra funções com mais de 30 linhas."""
        long_funcs = []

        for func in functions:
            func_lines = (func.end_lineno or func.lineno) - func.lineno + 1
            if func_lines > 30:
                long_funcs.append(
                    {
                        "name": func.name,
                        "lines": func_lines,
                        "params": len(func.args.args),
                    }
                )

        return sorted(long_funcs, key=lambda x: x["lines"], reverse=True)

    def _find_hardcoded_values(self, content: str) -> list[str]:
        """Encontra valores hardcoded que poderiam ser constantes."""
        hardcoded = []

        # Números mágicos
        magic_numbers = re.findall(r"\b\d{3,}\b", content)
        if magic_numbers:
            hardcoded.extend(
                [f"magic_number: {n}" for n in list(set(magic_numbers))[:5]]
            )

        # Strings constantes repetidas
        string_literals = re.findall(r'"([^"]{10,})"', content)
        for s in string_literals:
            if string_literals.count(s) > 1:
                hardcoded.append(f"repeated_string: {s[:30]}...")
                break

        # Magic paths
        if "http://" in content or "https://" in content:
            hardcoded.append("hardcoded_urls")

        return hardcoded[:10]

    def _find_duplicate_patterns(self, content: str) -> list[str]:
        """Encontra padrões duplicados."""
        patterns = []

        # Blocos de código similares (heurística)
        lines = content.split("\n")
        if len(lines) > 20:
            # Check for repeated import patterns
            import_lines = [
                ln for ln in lines if ln.strip().startswith("import") or "from" in ln
            ]
            if len(import_lines) > len(set(import_lines)):
                patterns.append("duplicate_imports")

        # Check for repeated if/elif blocks
        if_blocks = len(re.findall(r"if .+:", content))
        elif_blocks = len(re.findall(r"elif .+:", content))
        if if_blocks > 5 or elif_blocks > 3:
            patterns.append("multiple_conditionals")

        return patterns

    def _calculate_refactor_score(
        self, lines: int, classes: int, functions: int, issues: int, long_funcs: int
    ) -> float:
        """Calcula score de refatoração (0-100, quanto maior melhor)."""
        score = 100.0

        # Penalidades
        if lines > 200:
            score -= min(30, (lines - 200) / 20)  # até -30
        if classes == 0 and lines > 100:
            score -= 10  # sem classes em arquivo grande
        if functions > 10:
            score -= min(15, (functions - 10) / 5)  # muitas funções
        if long_funcs > 0:
            score -= min(20, long_funcs * 5)  # funções longas
        if issues > 2:
            score -= min(15, issues * 3)

        return max(0, score)

    def _print_file_summary(self, metrics: FileMetrics) -> None:
        """Imprime resumo de um arquivo."""
        icon = "⚠️ " if metrics.lines > 200 or metrics.issues else "✓ "
        print(f"{icon}{metrics.name:<40} | {metrics.lines:3d} linhas")
        if metrics.issues:
            for issue in metrics.issues[:2]:
                print(f"   → {issue}")

    def _generate_reports(self) -> None:
        """Gera relatórios de análise."""
        ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

        # Relatório 1: Discovery
        self._write_discovery()

        # Relatório 2: Analysis
        self._write_analysis()

        # Relatório 3: Recommendations
        self._write_recommendations()

        # Dados brutos (JSON)
        self._write_raw_data()

        print(f"\n{'=' * 70}")
        print("📊 Analysis complete!")
        print(f"📁 Reports saved to: {ANALYSIS_DIR}")
        print(f"{'=' * 70}\n")

    def _write_discovery(self) -> None:
        """Escreve relatório de descoberta."""
        files_by_size = sorted(self.files, key=lambda x: x.lines, reverse=True)
        large_files = [f for f in files_by_size if f.lines > 200]
        problem_files = [f for f in self.files if f.issues]

        content = f"""# Providence Runtime Module - Discovery Report

**Data**: {datetime.now().isoformat()}

## Sumário Executivo

- **Total de arquivos**: {len(self.files)}
- **Arquivos com >200 linhas**: {len(large_files)}
- **Arquivos com problemas identificados**: {len(problem_files)}
- **Score médio de refatoração**: {sum(f.refactor_score for f in self.files) / len(self.files):.1f}/100

## Arquivos Grandes (>200 linhas)

Candidatos para refatoração imediata:

"""
        for f in large_files:
            content += f"- `{f.name}`: {f.lines} linhas, score={f.refactor_score:.0f}\n"

        content += """

## Problemas Identificados

### Funções Longas (>30 linhas)

"""
        long_func_files = [f for f in self.files if f.long_functions]
        for f in long_func_files[:5]:
            content += f"- `{f.name}`:\n"
            for func in f.long_functions[:3]:
                content += f"  - `{func['name']}()`: {func['lines']} linhas\n"

        content += """

### Imports Pesados

"""
        heavy_import_files = [f for f in self.files if f.heavy_imports]
        for f in heavy_import_files:
            content += f"- `{f.name}`: {', '.join(f.heavy_imports)}\n"

        content += f"""

### Valores Hardcoded

Encontrados em {len([f for f in self.files if f.hardcoded_values])} arquivo(s)

### Padrões Duplicados

Encontrados em {len([f for f in self.files if f.duplicate_patterns])} arquivo(s)

## Próximas Etapas

1. Analisar em detalhe arquivos com >200 linhas
2. Extrair métodos de funções longas
3. Converter valores hardcoded em constantes
4. Resolver circular dependencies
5. Consolidar padrões duplicados

---

**Gerado por**: providence_runtime analyzer
**Timestamp**: {datetime.now().isoformat()}
"""

        write_text_utf8(ANALYSIS_DIR / "discovery.md", content)

    def _build_refactor_section(self, large_files: list[FileMetrics]) -> str:
        """Constrói a seção de arquivos candidatos para divisão."""
        section = ""
        for f in large_files:
            section += f"""
#### `{f.name}` ({f.lines} linhas)

**Métricas**:
- Classes: {f.classes}
- Funções: {f.functions}
- Refactor Score: {f.refactor_score:.0f}/100

**Problemas**:
"""
            for issue in f.issues:
                section += f"- {issue}\n"

            section += """
**Sugestão**: Dividir em submódulos ou extrair classes para arquivos separados

"""
        return section

    def _write_analysis(self) -> None:
        """Escreve análise detalhada."""
        content = f"""# Providence Runtime Module - Detailed Analysis

**Data**: {datetime.now().isoformat()}

## Dimensão 1: Refatoração

### Arquivos Candidatos para Divisão (>200 linhas)

"""
        large_files = sorted(
            [f for f in self.files if f.lines > 200],
            key=lambda x: x.lines,
            reverse=True,
        )

        content += self._build_refactor_section(large_files)

        content += """

## Dimensão 2: Performance

### Imports Pesados

Arquivos importando bibliotecas pesadas ou fazendo imports desnecessários:

"""
        for f in [f for f in self.files if f.heavy_imports]:
            content += f"- `{f.name}`: {', '.join(f.heavy_imports)}\n"

        content += """

**Recomendação**: Use lazy imports ou import local para bibliotecas pesadas

### Circular Dependencies

Potenciais dependências circulares detectadas:

"""
        circular_files = [f for f in self.files if f.circular_deps]
        if circular_files:
            for f in circular_files[:10]:
                content += f"- `{f.name}` → {', '.join(f.circular_deps[:3])}\n"
        else:
            content += "✓ Nenhuma circular dependency óbvia detectada\n"

        content += """

### Funções Longas (Complexidade)

Funções com mais de 30 linhas (candidatas para decomposição):

"""
        func_files = sorted(
            [f for f in self.files if f.long_functions],
            key=lambda x: sum(fn["lines"] for fn in x.long_functions),
            reverse=True,
        )
        for f in func_files[:5]:
            content += f"\n`{f.name}`:\n"
            for func in f.long_functions[:3]:
                content += f"  - {func['name']}(): {func['lines']} linhas, {func['params']} parâmetros\n"

        content += """

## Dimensão 3: Padronização & Reuso

### Valores Hardcoded

Valores que poderiam ser constantes:

"""
        hardcoded_files = [f for f in self.files if f.hardcoded_values]
        for f in hardcoded_files[:5]:
            content += f"- `{f.name}`:\n"
            for val in f.hardcoded_values[:3]:
                content += f"  - {val}\n"

        content += """

**Ação**: Criar módulo `constants.py` com valores centralizados

### Padrões Duplicados

Código que pode ser consolidado:

"""
        dup_files = [f for f in self.files if f.duplicate_patterns]
        for f in dup_files[:5]:
            content += f"- `{f.name}`: {', '.join(f.duplicate_patterns)}\n"

        content += """

---

**Gerado por**: providence_runtime analyzer
"""

        write_text_utf8(ANALYSIS_DIR / "analysis.md", content)

    def _write_recommendations(self) -> None:
        """Escreve recomendações."""
        large_files = sorted(
            [f for f in self.files if f.lines > 200],
            key=lambda x: x.lines,
            reverse=True,
        )

        content = f"""# Providence Runtime Module - Recommendations

**Data**: {datetime.now().isoformat()}

## Recomendações Priorizadas

### Phase 1: Refatoração Imediata

#### 1.1 Dividir Arquivos Grandes

Arquivos que excedem 200 linhas e devem ser refatorados:

"""
        for f in large_files[:5]:
            content += f"- `{f.name}` ({f.lines} linhas)\n"

        content += """

**Abordagem**:
- Extrair classes para arquivos separados
- Consolidar funções relacionadas em módulos temáticos
- Manter interface pública estável

#### 1.2 Decomposição de Funções Longas

Extrair métodos de funções com >30 linhas:

"""
        for f in self.files:
            if f.long_functions:
                content += f"- `{f.name}`:\n"
                for func in f.long_functions[:3]:
                    content += f"  - `{func['name']}()` ({func['lines']} linhas) → extrair submétodos\n"

        content += """

### Phase 2: Padronização

#### 2.1 Centralizar Constantes

Criar `constants.py`:

```python
# providence_runtime/constants.py

# Valores mágicos
DEFAULT_TIMEOUT = 30
DEFAULT_RETRY_COUNT = 3
DEFAULT_BUFFER_SIZE = 1024

# Strings constantes
ERROR_MESSAGES = {
    'timeout': 'Operation timed out',
    'invalid_input': 'Invalid input provided',
    # ...
}

# Padrões
VALID_STATES = ['pending', 'running', 'completed', 'failed']
```

#### 2.2 Consolidar Padrões Duplicados

"""
        dup_files = [f for f in self.files if f.duplicate_patterns]
        for f in dup_files[:5]:
            content += f"- `{f.name}`: {', '.join(f.duplicate_patterns)}\n"

        content += """

### Phase 3: Performance

#### 3.1 Lazy Imports

Para imports pesados, usar lazy loading:

```python
def expensive_operation():
    import pandas as pd  # Import local
    # usar pd
    return result
```

#### 3.2 Resolver Circular Dependencies

Revisar imports internos de `providence_runtime`:
"""
        circular_files = [f for f in self.files if f.circular_deps]
        if circular_files:
            for f in circular_files[:5]:
                content += f"- `{f.name}` ← {', '.join(f.circular_deps[:2])}\n"

        content += f"""

## Métricas de Sucesso

- [ ] Todos os arquivos < 200 linhas
- [ ] Todas as funções < 30 linhas
- [ ] Zero hardcoded values fora de constants.py
- [ ] Zero padrões duplicados
- [ ] Score refator médio > 80

## Timeline Estimado

- **Phase 1**: 2-3 sprints (refatoração estrutural)
- **Phase 2**: 1-2 sprints (padronização)
- **Phase 3**: 1 sprint (otimizações)

**Esforço Total**: ~3-4 FTE-weeks

---

**Gerado por**: providence_runtime analyzer
**Timestamp**: {datetime.now().isoformat()}
"""

        write_text_utf8(ANALYSIS_DIR / "recommendations.md", content)

    def _write_raw_data(self) -> None:
        """Escreve dados brutos em JSON."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_files": len(self.files),
            "analysis_dir": str(RUNTIME_DIR),
            "files": [asdict(f) for f in self.files],
            "summary": {
                "total_lines": sum(f.lines for f in self.files),
                "total_classes": sum(f.classes for f in self.files),
                "total_functions": sum(f.functions for f in self.files),
                "large_files": len([f for f in self.files if f.lines > 200]),
                "avg_refactor_score": sum(f.refactor_score for f in self.files)
                / len(self.files),
            },
        }

        write_text_utf8(ANALYSIS_DIR / "analysis.json", json.dumps(data, indent=2))


def main() -> None:
    analyzer = RuntimeAnalyzer()
    analyzer.analyze_all()


if __name__ == "__main__":
    main()
