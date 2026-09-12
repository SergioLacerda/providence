#!/bin/bash
set -e

echo "🚀 Configurando ambiente Providence..."

# Instala uv via pip (sem curl-pipe-to-shell; PyPI verifica assinaturas do pacote)
python3 -m pip install --quiet uv

# Sincroniza dependências
uv sync --all-groups

# Instala pre-commit hooks
uv run pre-commit install --install-hooks

# Verifica se o SDD CLI está funcionando
echo "✅ Verificando SDD CLI..."
uv run providence --version || echo "⚠️  SDD CLI ainda não instalado como pacote editável"

echo "=========================================="
echo "✅ Ambiente Providence configurado com sucesso!"
echo "Comandos úteis:"
echo "   uv run providence doctor run"
echo "   uv run providence governance compile"
echo "   make help"
echo "=========================================="
