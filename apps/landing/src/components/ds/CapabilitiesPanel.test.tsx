// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { render, screen, cleanup, fireEvent } from '@testing-library/react';
import { CapabilitiesPanel } from './CapabilitiesPanel';
import { setLang } from '../../lib/lang-bridge';
import type { GovernanceStats } from '../../lib/governance-stats';

const REAL_STATS: GovernanceStats = {
  mandatesCount: 16,
  guidelinesCount: 23,
  fingerprintShort: 'f95a…b222',
  available: true,
};

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
});

describe('CapabilitiesPanel', () => {
  it('renders all four article tabs in Portuguese', () => {
    render(<CapabilitiesPanel stats={REAL_STATS} />);
    expect(screen.getByText('I. Auditoria')).toBeInTheDocument();
    expect(screen.getByText('II. Context-aware')).toBeInTheDocument();
    expect(screen.getByText('III. Cross-learning')).toBeInTheDocument();
    expect(screen.getByText('IV. Compilação')).toBeInTheDocument();
  });

  it('defaults to the audit tab, with real stats substituted into the terminal output', () => {
    render(<CapabilitiesPanel stats={REAL_STATS} />);
    expect(screen.getByText('Auditoria: drift & economia de tokens')).toBeInTheDocument();
    expect(screen.getByText('fingerprint f95a…b222')).toBeInTheDocument();
  });

  it('switches to the context tab on click', () => {
    render(<CapabilitiesPanel stats={REAL_STATS} />);
    fireEvent.click(screen.getByText('II. Context-aware'));
    expect(
      screen.getByText('Context-aware: cache isolado por projeto'),
    ).toBeInTheDocument();
  });

  it('switches to the cross-learning tab on click', () => {
    render(<CapabilitiesPanel stats={REAL_STATS} />);
    fireEvent.click(screen.getByText('III. Cross-learning'));
    expect(
      screen.getByText('Cross-learning em runtime: células isoladas + handshake'),
    ).toBeInTheDocument();
  });

  it('switches to the compile tab on click, substituting real stats into compStats', () => {
    render(<CapabilitiesPanel stats={REAL_STATS} />);
    fireEvent.click(screen.getByText('IV. Compilação'));
    expect(
      screen.getByText('Compilação: otimizada, assinada, com fingerprint'),
    ).toBeInTheDocument();
    expect(screen.getByText('f95a…b222')).toBeInTheDocument();
  });

  it('falls back to placeholder stats when none are passed', () => {
    render(<CapabilitiesPanel />);
    expect(screen.getByText('fingerprint —')).toBeInTheDocument();
  });

  it('switches to English tab labels and content when the lang bridge broadcasts a change', async () => {
    render(<CapabilitiesPanel stats={REAL_STATS} />);
    setLang('en');
    expect(await screen.findByText('I. Audit')).toBeInTheDocument();
    expect(screen.getByText('Audit: drift & token economy')).toBeInTheDocument();
  });
});
