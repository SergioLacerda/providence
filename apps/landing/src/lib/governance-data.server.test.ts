import { afterEach, describe, expect, it, vi } from 'vitest';

// governance-data.server.ts resolves .providence/metadata.json from its own module
// location (import.meta.url) with no injectable override, and modifying it
// is outside this mission's approved scope (see
// .analysis/refined/vitest-landing-testing-20260702/proposal.md). That
// leaves no path-injection point for a real temp-file fixture, so — despite
// design.md recording a real temp file as the default — mocking `node:fs`
// is used here instead, which is the documented fallback strategy.
vi.mock('node:fs', () => ({
  readFileSync: vi.fn(),
}));

afterEach(() => {
  vi.resetModules();
  vi.clearAllMocks();
});

async function loadWithMockedFs(readFileSyncImpl: () => string) {
  const fs = await import('node:fs');
  vi.mocked(fs.readFileSync).mockImplementation(readFileSyncImpl as never);
  const { loadGovernanceStats } = await import('./governance-data.server');
  return loadGovernanceStats();
}

describe('loadGovernanceStats — real read path', () => {
  it('returns real stats when metadata.json is valid', async () => {
    const stats = await loadWithMockedFs(() =>
      JSON.stringify({
        mandates_count: 16,
        guidelines_count: 23,
        fingerprints: { combined: 'f95a3c901a84b222' },
      }),
    );
    expect(stats).toEqual({
      mandatesCount: 16,
      guidelinesCount: 23,
      fingerprintShort: 'f95a…b222',
      available: true,
    });
  });
});

describe('loadGovernanceStats — fallback path', () => {
  it('falls back when the file is missing (readFileSync throws)', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const stats = await loadWithMockedFs(() => {
      throw new Error('ENOENT: no such file or directory');
    });
    expect(stats).toEqual({
      mandatesCount: 0,
      guidelinesCount: 0,
      fingerprintShort: '—',
      available: false,
    });
    expect(warn).toHaveBeenCalledOnce();
    warn.mockRestore();
  });

  it('falls back when the file contains malformed JSON', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const stats = await loadWithMockedFs(() => '{not valid json');
    expect(stats.available).toBe(false);
    warn.mockRestore();
  });

  it('falls back when a required field is missing', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const stats = await loadWithMockedFs(() =>
      JSON.stringify({
        mandates_count: 16,
        // guidelines_count missing
        fingerprints: { combined: 'f95a3c901a84b222' },
      }),
    );
    expect(stats.available).toBe(false);
    warn.mockRestore();
  });

  it('falls back when the fingerprint is missing', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const stats = await loadWithMockedFs(() =>
      JSON.stringify({
        mandates_count: 16,
        guidelines_count: 23,
        fingerprints: {},
      }),
    );
    expect(stats.available).toBe(false);
    warn.mockRestore();
  });
});
