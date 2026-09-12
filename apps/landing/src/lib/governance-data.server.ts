/**
 * Server-only: reads real governance stats from `.providence/metadata.json` at
 * build time. Import this only from `.astro` frontmatter (never from a
 * client-hydrated component) — it uses Node built-ins that don't exist in
 * the browser bundle.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import {
  PLACEHOLDER_GOVERNANCE_STATS,
  type GovernanceStats,
} from './governance-stats';

const MAX_MARKER_SEARCH_DEPTH = 12;

/**
 * Walks upward from `startDir` looking for a `.git` entry — a directory in a
 * normal checkout, a file in a worktree/submodule — as a repo-root marker.
 * Unlike a fixed relative hop count, this is independent of how deep a
 * bundler nests this module's compiled chunk relative to its source
 * location (see docs/migration/2026-09-07-repo-root-resolution-fix.md: a
 * fixed `../../../..` broke under `astro build`, whose SSR/prerender
 * bundler places the chunk one directory level deeper than
 * `src/lib/governance-data.server.ts`).
 *
 * Uses only `readFileSync` (no `existsSync`/`statSync`) so the existing
 * `vi.mock('node:fs', () => ({ readFileSync: vi.fn() }))` pattern in
 * governance-data.server.test.ts keeps working unmodified: any successful
 * read (any content) or an `EISDIR` error both count as "found `.git` here";
 * `ENOENT` means "keep looking upward". Never throws and never logs — a
 * failed search silently falls through to the caller's own fallback.
 */
function findRepoRootByGitMarker(startDir: string): string | null {
  let dir = startDir;
  for (let i = 0; i < MAX_MARKER_SEARCH_DEPTH; i += 1) {
    try {
      readFileSync(path.join(dir, '.git'));
      return dir;
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code === 'EISDIR') return dir;
    }
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
  return null;
}

const MODULE_DIR = path.dirname(fileURLToPath(import.meta.url));
// Legacy fallback, kept only in case the `.git` marker search fails outright
// (e.g. a deployment that ships without git history) — never worse than the
// previous, always-fixed-depth behavior.
const LEGACY_REPO_ROOT = path.resolve(MODULE_DIR, '../../../..');
const REPO_ROOT =
  process.env.SDD_REPO_ROOT ??
  findRepoRootByGitMarker(MODULE_DIR) ??
  LEGACY_REPO_ROOT;
const METADATA_PATH = path.join(REPO_ROOT, '.providence', 'metadata.json');

function shortenFingerprint(fingerprint: string): string {
  if (fingerprint.length <= 12) return fingerprint;
  return `${fingerprint.slice(0, 4)}…${fingerprint.slice(-4)}`;
}

/**
 * Loads real governance stats. Falls back to placeholder stats (with a
 * build warning) if `.providence/metadata.json` isn't present — mirrors the
 * fallback behavior of `selector_compiler.py`, which never ships fake data
 * as if it were real.
 */
export function loadGovernanceStats(): GovernanceStats {
  try {
    const raw = readFileSync(METADATA_PATH, 'utf-8');
    const metadata = JSON.parse(raw) as {
      mandates_count?: number;
      guidelines_count?: number;
      fingerprints?: { combined?: string };
    };
    const fingerprint = metadata.fingerprints?.combined;
    if (
      typeof metadata.mandates_count !== 'number' ||
      typeof metadata.guidelines_count !== 'number' ||
      !fingerprint
    ) {
      throw new Error('metadata.json is missing required governance fields');
    }
    return {
      mandatesCount: metadata.mandates_count,
      guidelinesCount: metadata.guidelines_count,
      fingerprintShort: shortenFingerprint(fingerprint),
      available: true,
    };
  } catch (err) {
    console.warn(
      `[governance-data] .providence/metadata.json not readable at ${METADATA_PATH} ` +
        `(${(err as Error).message}). Run 'sdd governance generate' before building ` +
        'for production. Falling back to placeholder stats.',
    );
    return PLACEHOLDER_GOVERNANCE_STATS;
  }
}
