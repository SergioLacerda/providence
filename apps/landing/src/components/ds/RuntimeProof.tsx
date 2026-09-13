import { useEffect, useState } from 'react';
import { GovernanceFooter } from './GovernanceFooter';
import { LANDING_CONTENT, RUNTIME_PROOF_CONTENT, type Lang } from '../../lib/i18n';
import { withGovernanceStats, PLACEHOLDER_GOVERNANCE_STATS, type GovernanceStats } from '../../lib/governance-stats';
import { getLang, onLangChange } from '../../lib/lang-bridge';

interface RuntimeProofProps {
  stats?: GovernanceStats;
  detailHref: string;
}

/**
 * Compact "prove it live" strip for index.astro — the custody seal (real
 * mandate/guideline counts), GovernanceFooter trailer, and the 4-step "how it
 * works" list, all that survives from the old single-page Landing.tsx hero
 * once the full audit/context/cross-learning/compile deep dive moved to
 * CapabilitiesPanel on detalhe-tecnico (see design.md's index.astro
 * recommendation in the migration spec).
 */
export function RuntimeProof({ stats = PLACEHOLDER_GOVERNANCE_STATS, detailHref }: RuntimeProofProps) {
  const [lang, setLangState] = useState<Lang>('pt');
  useEffect(() => {
    setLangState(getLang());
    return onLangChange(setLangState);
  }, []);

  const p = RUNTIME_PROOF_CONTENT[lang];
  const c = LANDING_CONTENT[lang];

  return (
    <section id="runtime-proof">
      <div className="wrap" style={{ textAlign: 'center' }}>
        <p className="eyebrow">{p.eyebrow}</p>
        <h2 style={{ margin: '0 auto 16px' }}>{p.title}</h2>
        <p style={{ margin: '0 auto 48px', color: 'var(--ink-dim)', maxWidth: '58ch', fontSize: 15.5 }}>{p.intro}</p>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 22, marginBottom: 40 }}>
          <svg width={110} height={110} viewBox="0 0 200 200" aria-hidden="true">
            <circle cx={100} cy={100} r={94} fill="none" stroke="var(--line-strong)" strokeWidth={1} />
            <circle cx={100} cy={100} r={76} fill="none" stroke="var(--line-strong)" strokeWidth={1} />
            <path d="M100 176 A76 76 0 0 1 100 24" fill="none" stroke="var(--steel)" strokeWidth={1.8} />
            <path d="M100 24 A76 76 0 0 1 100 176" fill="none" stroke="var(--clean)" strokeWidth={1.8} />
            <line x1={100} y1={24} x2={100} y2={176} stroke="var(--line-strong)" strokeWidth={1} />
            <line x1={24} y1={100} x2={176} y2={100} stroke="var(--line)" strokeWidth={1} />
            <circle cx={100} cy={100} r={3} fill="var(--bronze-bright)" />
          </svg>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14, textAlign: 'left' }}>
            <div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>{withGovernanceStats(stats, 'M001–M{{MCOUNT}}')}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', color: 'var(--ink-faint)', textTransform: 'uppercase', marginTop: 2 }}>{c.legendMandate}</div>
            </div>
            <div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink)' }}>{withGovernanceStats(stats, 'G01–G{{GCOUNT}}')}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, letterSpacing: '.08em', color: 'var(--ink-faint)', textTransform: 'uppercase', marginTop: 2 }}>{c.legendGuideline}</div>
            </div>
          </div>
        </div>

        <div style={{ display: 'inline-flex', marginBottom: 44 }}>
          <GovernanceFooter drift="clean" governance="active" profile="client" surface="dark" />
        </div>

        <div className="steps-grid">
          {c.steps.map((s, i) => (
            <div key={s.roman} className="step-cell" style={{ borderRight: i < c.steps.length - 1 ? '1px solid var(--line)' : 'none' }}>
              <div style={{ width: 34, height: 34, borderRadius: 999, border: '1px solid var(--bronze-dim)', color: 'var(--bronze)', fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>{s.roman}</div>
              <h3 style={{ margin: '0 0 6px', fontFamily: 'var(--serif)', fontSize: 15.5, fontWeight: 600, color: 'var(--ink)' }}>{s.t}</h3>
              <p style={{ margin: '0 0 14px', fontSize: 13, lineHeight: 1.5, color: 'var(--ink-dim)' }}>{withGovernanceStats(stats, s.d)}</p>
              <code style={{ display: 'inline-block', fontFamily: 'var(--mono)', fontSize: 11.5, color: 'var(--bronze-bright)', background: 'var(--panel-2)', border: '1px solid var(--line)', borderRadius: 4, padding: '6px 10px', wordBreak: 'break-word' }}>{s.cmd}</code>
            </div>
          ))}
        </div>

        <style>{`
          .steps-grid{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0;
            border: 1px solid var(--line-strong);
            border-radius: 4px;
            overflow: hidden;
            text-align: left;
          }
          .step-cell{ padding: 22px 20px; background: var(--panel); }
          @media (max-width: 760px){
            .steps-grid{ grid-template-columns: 1fr; }
            .step-cell{ border-right: none !important; border-bottom: 1px solid var(--line); }
            .step-cell:last-child{ border-bottom: none; }
          }
        `}</style>

        <a
          href={detailHref}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 8, marginTop: 40,
            fontFamily: 'var(--mono)', fontSize: 13, color: 'var(--bronze-bright)', textDecoration: 'none',
          }}
        >
          {p.detailCta}
        </a>
      </div>
    </section>
  );
}
