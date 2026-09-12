"""CLI entry points for providence_pages: publish, index, compress, audit, validate-index.

Deferred scope (documented):
- search.index.json workflow integration: `search-index` CLI command exists and is
  functional, but CI does not yet call it automatically. Deferred until a search
  consumer (e.g. site search widget) is wired up; add a Makefile target that chains
  `sdd pages index` and `sdd pages search-index` when that integration lands.
- DeltaIndexer / cache workflow integration: `DeltaIndexer` and `cached_index` APIs
  exist in providence_pages.delta and are fully tested. They are not called from CI because
  incremental indexing only improves cold-start performance at large doc set sizes (>200
  files); the current docs corpus is small enough that a full re-index on each CI run
  is acceptable. Integrate when corpus growth makes full-index time noticeable.
"""

from __future__ import annotations

from pathlib import Path

import typer

from providence_pages.compression import DEFAULT_THRESHOLD_BYTES, CompressionEngine
from providence_pages.metadata import MetadataExtractor
from providence_pages.publisher import GitHubPagesPublisher
from providence_pages.selector import DEFAULT_GLOB, DocumentIndexer
from providence_pages.validator import IndexValidator

app = typer.Typer(name="pages", help="GitHub Pages publishing and asset commands.")


@app.command()
def publish(
    source_dir: Path = typer.Argument(..., help="Directory to publish."),
    branch: str = typer.Option("gh-pages", help="Target branch."),
    remote: str = typer.Option("origin", help="Git remote name."),
) -> None:
    """Publish a directory to GitHub Pages."""
    publisher = GitHubPagesPublisher(remote=remote)
    result = publisher.publish(source_dir, branch=branch)
    if result.success:
        typer.echo(f"Published {source_dir} to {remote}/{branch}")
    else:
        typer.echo(f"Publish failed: {result.message}", err=True)
        raise typer.Exit(code=1)


@app.command(name="index")
def build_index(
    source_dir: Path = typer.Argument(..., help="Directory to index."),
    output: Path = typer.Option(Path("index.json"), help="Output JSON path."),
    glob: str = typer.Option(DEFAULT_GLOB, help="Glob pattern for documents."),
) -> None:
    """Build a document index for source_dir."""
    indexer = DocumentIndexer()
    entries = indexer.index(source_dir, glob=glob)
    indexer.to_json(entries, output)
    typer.echo(f"Indexed {len(entries)} documents -> {output}")


@app.command()
def compress(
    source_dir: Path = typer.Argument(..., help="Directory whose files to compress."),
    glob: str = typer.Option("**/*", help="Glob pattern for files to compress."),
    threshold: int = typer.Option(
        DEFAULT_THRESHOLD_BYTES, help="Minimum file size (bytes) to gzip."
    ),
    manifest: Path = typer.Option(
        Path(".compressed/manifest.json"), help="Manifest output path."
    ),
) -> None:
    """Compress files under source_dir with gzip and write a manifest."""
    engine = CompressionEngine()
    results = []
    for file_path in sorted(source_dir.glob(glob)):
        if not file_path.is_file():
            continue
        result = engine.compress_gzip(file_path, threshold=threshold)
        if result is not None:
            results.append(result)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    engine.generate_manifest(results, manifest)
    typer.echo(f"Compressed {len(results)} files -> {manifest}")


@app.command(name="search-index")
def build_search_index(
    source_dir: Path = typer.Argument(..., help="Directory to index."),
    output: Path = typer.Option(Path("search.index.json"), help="Output JSON path."),
    glob: str = typer.Option(DEFAULT_GLOB, help="Glob pattern for documents."),
) -> None:
    """Build a full-text search index including document body text."""
    indexer = DocumentIndexer()
    entries = indexer.index(source_dir, glob=glob)
    indexer.to_search_json(entries, source_dir, output)
    typer.echo(f"Search index: {len(entries)} documents -> {output}")


@app.command(name="validate-index")
def validate_index(
    index_path: Path = typer.Argument(..., help="Path to docs.index.json to validate."),
    source_dir: Path = typer.Option(
        None, help="Source directory for existence checks."
    ),
) -> None:
    """Validate a docs.index.json file for schema and consistency."""
    result = IndexValidator().validate(index_path, source_dir=source_dir)
    for error in result.errors:
        typer.echo(f"ERROR: {error}", err=True)
    for warning in result.warnings:
        typer.echo(f"WARNING: {warning}")
    if result.valid:
        typer.echo("Index is valid.")
    else:
        raise typer.Exit(code=1)


@app.command()
def audit(
    source_dir: Path = typer.Argument(..., help="Directory to audit."),
    glob: str = typer.Option(DEFAULT_GLOB, help="Glob pattern for documents."),
) -> None:
    """Audit documents for missing metadata."""
    extractor = MetadataExtractor()
    missing_title: list[str] = []
    total = 0
    for file_path in sorted(source_dir.glob(glob)):
        if not file_path.is_file():
            continue
        total += 1
        metadata = extractor.extract(file_path)
        if not metadata.title:
            missing_title.append(str(file_path.relative_to(source_dir)))

    typer.echo(f"Audited {total} documents")
    if missing_title:
        typer.echo(f"Missing title metadata ({len(missing_title)}):")
        for rel_path in missing_title:
            typer.echo(f"  - {rel_path}")
        raise typer.Exit(code=1)
    typer.echo("No issues found")
