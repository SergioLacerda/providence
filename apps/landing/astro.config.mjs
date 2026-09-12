import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// https://docs.astro.build/en/reference/configuration-reference/
export default defineConfig({
  integrations: [react()],
  output: 'static',
  site: 'https://sergiolacerda.github.io/providence/',
  base: '/providence/',
  // Output straight into the shared publication root used by the docs
  // pipeline (see mkdocs.yml `site_dir` and .github/workflows/docs.yml).
  // MkDocs writes to build/site/docs/, the Selector compiler writes to
  // build/site/selector/ — this build must not touch either subtree.
  outDir: '../../build/site',
  vite: {
    build: {
      // Vite/Astro empties outDir by default, which would delete the
      // MkDocs and Selector output already written into the same shared
      // build/site/ root. This build only ever adds its own files
      // (index.html, _astro/, assets/) and must not clean siblings.
      emptyOutDir: false,
    },
  },
});
