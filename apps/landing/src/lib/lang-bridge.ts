/**
 * Cross-island language bridge. The Providentian chrome (SiteNav, VirtuesWheel,
 * plain Astro pages) and the remaining React islands (CapabilitiesPanel) each
 * render independently across 3 separate pages — there's no single top-level
 * React tree to hold `lang` state anymore (see docs/migration/2026-09-07-
 * landing-page-providentia-migration.md, "what must not silently break").
 * This module is the shared source of truth: persisted to localStorage,
 * broadcast via a DOM CustomEvent so both vanilla-JS and React listeners can
 * react without a full page reload.
 */
import type { Lang } from './i18n';

const STORAGE_KEY = 'pv-lang';
const EVENT_NAME = 'pv:langchange';

export function getLang(): Lang {
  if (typeof window === 'undefined') return 'pt';
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === 'en' ? 'en' : 'pt';
}

export function setLang(lang: Lang): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(STORAGE_KEY, lang);
  document.documentElement.lang = lang === 'pt' ? 'pt-BR' : 'en';
  window.dispatchEvent(new CustomEvent<Lang>(EVENT_NAME, { detail: lang }));
}

export function onLangChange(callback: (lang: Lang) => void): () => void {
  if (typeof window === 'undefined') return () => {};
  const handler = (event: Event) => callback((event as CustomEvent<Lang>).detail);
  window.addEventListener(EVENT_NAME, handler);
  return () => window.removeEventListener(EVENT_NAME, handler);
}
