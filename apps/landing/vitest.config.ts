import { defineConfig } from 'vitest/config';

// Standalone config (not astro/config's getViteConfig()) — scope is
// logic-only tests in src/lib/ plus React-island component tests, so the
// full Astro Vite pipeline isn't needed. See
// .analysis/refined/vitest-landing-testing-20260702/design.md for the
// original src/lib/-only scope; React-island coverage (happy-dom +
// @testing-library/react) was added for the T-2–T-6 Providentian migration
// (docs/migration/2026-09-07-landing-page-providentia-migration.md) —
// Astro-component testing (SiteNav, VirtuesWheel, etc., via the Astro
// Container API) is a deliberately separate, not-yet-taken step, same
// doctrine as the original mission's "happy-dom is a future choice" note.
// Default environment stays 'node' (matches src/lib/governance-data.server's
// Node-only fs code); component test files opt into
// `// @vitest-environment happy-dom` individually instead of paying the DOM
// setup cost for every test file.
export default defineConfig({
  test: {
    include: ['src/lib/**/*.test.ts', 'src/components/**/*.test.tsx'],
    setupFiles: ['./vitest.setup.ts'],
    coverage: {
      provider: 'v8',
      // Scoped to modules with an actual test plan — not all of src/lib/**
      // or src/components/**, since src/lib/i18n.ts is static copy/content
      // data and the Astro components (SiteNav, VirtuesWheel, BrandLogo,
      // ScrollSectionNav, InstallCard) are out of scope for this round (see
      // module comment above).
      include: [
        'src/lib/governance-stats.ts',
        'src/lib/governance-data.server.ts',
        'src/lib/lang-bridge.ts',
        'src/components/ds/CapabilitiesPanel.tsx',
        'src/components/ds/RuntimeProof.tsx',
      ],
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 70,
        statements: 70,
      },
    },
  },
});
