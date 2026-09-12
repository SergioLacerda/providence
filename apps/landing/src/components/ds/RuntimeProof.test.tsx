// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { RuntimeProof } from './RuntimeProof';
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

describe('RuntimeProof', () => {
  it('renders Portuguese copy by default', () => {
    render(<RuntimeProof stats={REAL_STATS} detailHref="/detalhe-tecnico" />);
    expect(screen.getByText('prova em runtime')).toBeInTheDocument();
    expect(
      screen.getByText('Não é só filosofia — roda junto com o agente'),
    ).toBeInTheDocument();
  });

  it('renders real governance stats via withGovernanceStats, not placeholders', () => {
    render(<RuntimeProof stats={REAL_STATS} detailHref="/detalhe-tecnico" />);
    expect(screen.getByText('M001–M016')).toBeInTheDocument();
    expect(screen.getByText('G01–G23')).toBeInTheDocument();
  });

  it('falls back to placeholder stats when none are passed', () => {
    render(<RuntimeProof detailHref="/detalhe-tecnico" />);
    expect(screen.getByText('M001–M000')).toBeInTheDocument();
  });

  it('renders the GovernanceFooter trailer', () => {
    render(<RuntimeProof stats={REAL_STATS} detailHref="/detalhe-tecnico" />);
    expect(screen.getByText(/PROVIDENCE GOVERNANCE:/)).toBeInTheDocument();
  });

  it('renders the "how it works" steps with real stat substitution in the command copy', () => {
    render(<RuntimeProof stats={REAL_STATS} detailHref="/detalhe-tecnico" />);
    expect(
      screen.getByText(/Mandates imutáveis \(M001–M016\)/),
    ).toBeInTheDocument();
  });

  it('links the detail CTA to the given href with the Portuguese label', () => {
    render(<RuntimeProof stats={REAL_STATS} detailHref="/detalhe-tecnico" />);
    const link = screen.getByRole('link', { name: 'Ver detalhe técnico →' });
    expect(link).toHaveAttribute('href', '/detalhe-tecnico');
  });

  it('switches to English content when the lang bridge broadcasts a change', async () => {
    render(<RuntimeProof stats={REAL_STATS} detailHref="/detalhe-tecnico" />);
    expect(screen.getByText('prova em runtime')).toBeInTheDocument();

    setLang('en');

    expect(await screen.findByText('runtime proof')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'See technical detail →' }),
    ).toBeInTheDocument();
  });
});
