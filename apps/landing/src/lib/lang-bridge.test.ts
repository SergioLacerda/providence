// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getLang, setLang, onLangChange } from './lang-bridge';

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.lang = '';
});

describe('getLang', () => {
  it('defaults to "pt" when nothing is stored', () => {
    expect(getLang()).toBe('pt');
  });

  it('returns "en" when stored', () => {
    window.localStorage.setItem('pv-lang', 'en');
    expect(getLang()).toBe('en');
  });

  it('defaults to "pt" for any other stored value', () => {
    window.localStorage.setItem('pv-lang', 'garbage');
    expect(getLang()).toBe('pt');
  });
});

describe('setLang', () => {
  it('persists the language to localStorage', () => {
    setLang('en');
    expect(window.localStorage.getItem('pv-lang')).toBe('en');
  });

  it('sets <html lang> to "en" for English', () => {
    setLang('en');
    expect(document.documentElement.lang).toBe('en');
  });

  it('sets <html lang> to "pt-BR" for Portuguese', () => {
    setLang('pt');
    expect(document.documentElement.lang).toBe('pt-BR');
  });

  it('broadcasts a pv:langchange CustomEvent with the new language', () => {
    const handler = vi.fn();
    window.addEventListener('pv:langchange', handler);
    setLang('en');
    expect(handler).toHaveBeenCalledOnce();
    const event = handler.mock.calls[0][0] as CustomEvent<string>;
    expect(event.detail).toBe('en');
    window.removeEventListener('pv:langchange', handler);
  });
});

describe('onLangChange', () => {
  it('invokes the callback with the new language on change', () => {
    const callback = vi.fn();
    onLangChange(callback);
    setLang('en');
    expect(callback).toHaveBeenCalledWith('en');
  });

  it('the returned unsubscribe function stops further notifications', () => {
    const callback = vi.fn();
    const unsubscribe = onLangChange(callback);
    unsubscribe();
    setLang('en');
    expect(callback).not.toHaveBeenCalled();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });
});
