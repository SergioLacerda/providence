import React, { useEffect, useState } from 'react';
import { Terminal } from './Terminal';
import { LANDING_CONTENT, TERM_AUDIT, TERM_COMPILE, type Lang } from '../../lib/i18n';
import { withGovernanceStats, PLACEHOLDER_GOVERNANCE_STATS, type GovernanceStats } from '../../lib/governance-stats';
import { getLang, onLangChange } from '../../lib/lang-bridge';

type CapTab = 'audit' | 'context' | 'runtime' | 'compile';

interface CapabilitiesPanelProps {
  stats?: GovernanceStats;
}

/**
 * The full audit / context-aware / cross-learning / compile deep dive,
 * extracted from the old single-page Landing.tsx (see git history) onto the
 * detalhe-tecnico page as part of the T-2–T-6 Providentian migration
 * (docs/migration/2026-09-07-landing-page-providentia-migration.md). Reads
 * language from the shared lang bridge instead of owning its own top-level
 * tab state, since it no longer shares a React tree with SiteNav.
 */
export function CapabilitiesPanel({ stats = PLACEHOLDER_GOVERNANCE_STATS }: CapabilitiesPanelProps) {
  const [lang, setLangState] = useState<Lang>('pt');
  const [tab, setTab] = useState<CapTab>('audit');

  useEffect(() => {
    setLangState(getLang());
    return onLangChange(setLangState);
  }, []);

  const c = LANDING_CONTENT[lang];
  const termAuditLive = TERM_AUDIT.map((l) => ({ ...l, text: withGovernanceStats(stats, l.text) }));
  const termCompileLive = TERM_COMPILE.map((l) => ({ ...l, text: withGovernanceStats(stats, l.text) }));

  const articleTabStyle = (active: boolean): React.CSSProperties => ({
    background: 'none', border: 'none', cursor: 'pointer', padding: '0 0 14px',
    fontFamily: 'var(--mono)', fontSize: 13, letterSpacing: '.03em', marginBottom: -1,
    color: active ? 'var(--ink)' : 'var(--ink-faint)',
    borderBottom: `2px solid ${active ? 'var(--bronze)' : 'transparent'}`,
  });

  return (
    <div style={{ maxWidth: 940, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'center', gap: 36, borderBottom: '1px solid var(--line)', marginBottom: 40 }}>
        <button type="button" onClick={() => setTab('audit')} style={articleTabStyle(tab === 'audit')}>I. {c.tabAudit}</button>
        <button type="button" onClick={() => setTab('context')} style={articleTabStyle(tab === 'context')}>II. {c.tabContext}</button>
        <button type="button" onClick={() => setTab('runtime')} style={articleTabStyle(tab === 'runtime')}>III. {c.tabRuntime}</button>
        <button type="button" onClick={() => setTab('compile')} style={articleTabStyle(tab === 'compile')}>IV. {c.tabCompile}</button>
      </div>

      {tab === 'audit' && (
        <div>
          <h3 style={{ margin: '0 0 10px', fontFamily: 'var(--serif)', fontSize: 21, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--ink)', textAlign: 'center' }}>{c.auditTitle}</h3>
          <p style={{ margin: '0 auto 28px', fontSize: 15, lineHeight: 1.65, color: 'var(--ink-dim)', maxWidth: 640, textAlign: 'center' }}>{c.auditBody}</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 36, alignItems: 'start' }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {c.zones.map((z) => (
                <div key={z.zone} style={{ display: 'grid', gridTemplateColumns: '90px 76px 1fr', gap: 14, alignItems: 'center', padding: '13px 0', borderTop: '1px solid var(--line)' }}>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink)', display: 'flex', alignItems: 'center', gap: 7 }}>
                    <span style={{ width: 6, height: 6, borderRadius: 999, background: z.dot }} />{z.zone}
                  </span>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink-faint)' }}>{z.range}</span>
                  <span style={{ fontSize: 13, color: 'var(--ink-dim)', lineHeight: 1.4 }}>{z.action}</span>
                </div>
              ))}
              <p style={{ margin: '16px 0 0', fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink-faint)' }}>{c.auditCaption}</p>
            </div>
            <Terminal title="sdd — audit" chrome lines={termAuditLive} />
          </div>
        </div>
      )}

      {tab === 'context' && (
        <div>
          <h3 style={{ margin: '0 0 10px', fontFamily: 'var(--serif)', fontSize: 21, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--ink)', textAlign: 'center' }}>{c.ctxTitle}</h3>
          <p style={{ margin: '0 auto 28px', fontSize: 15, lineHeight: 1.65, color: 'var(--ink-dim)', maxWidth: 640, textAlign: 'center' }}>{c.ctxBody}</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 36, alignItems: 'start' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {c.ctxPoints.map((p) => (
                <div key={p.k} style={{ borderTop: '1px solid var(--line)', paddingTop: 14 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)', marginBottom: 4 }}>{p.k}</div>
                  <div style={{ fontSize: 13, lineHeight: 1.55, color: 'var(--ink-faint)' }}>{p.d}</div>
                </div>
              ))}
            </div>
            <div style={{ background: 'var(--term-bg)', borderRadius: 4, border: '1px solid var(--term-border)', padding: '18px 20px' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--term-dim)', marginBottom: 12 }}>.providence/task-context.json</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {c.cacheFields.map((f) => (
                  <div key={f.key}>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 13, color: 'var(--term-blue)' }}>{f.key}</span>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--term-dim)', lineHeight: 1.5 }}>{f.desc}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'runtime' && (
        <div>
          <h3 style={{ margin: '0 0 10px', fontFamily: 'var(--serif)', fontSize: 21, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--ink)', textAlign: 'center' }}>{c.crossTitle}</h3>
          <p style={{ margin: '0 auto 30px', fontSize: 15, lineHeight: 1.65, color: 'var(--ink-dim)', maxWidth: 640, textAlign: 'center' }}>{c.crossBody}</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 24, alignItems: 'center' }}>
            <div style={{ border: '1px solid var(--line-strong)', borderRadius: 4, padding: 20 }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--steel)', marginBottom: 10 }}>{c.cellA}</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)', marginBottom: 4 }}>{c.cellAgent}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink-faint)' }}>.providence/task-context.json</div>
              <div style={{ marginTop: 12, fontSize: 12, color: 'var(--ink-faint)', lineHeight: 1.5 }}>{c.cellIsolated}</div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, minWidth: 110 }}>
              <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--ink-faint)' }}>M015</span>
              <span style={{ width: 1, height: 34, background: 'var(--line-strong)' }} />
              <span style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--ink-faint)', textAlign: 'center' }}>{c.handshake}</span>
            </div>
            <div style={{ border: '1px solid var(--line-strong)', borderRadius: 4, padding: 20 }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--clean)', marginBottom: 10 }}>{c.cellB}</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)', marginBottom: 4 }}>{c.cellAgent}</div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--ink-faint)' }}>.providence/task-context.json</div>
              <div style={{ marginTop: 12, fontSize: 12, color: 'var(--ink-faint)', lineHeight: 1.5 }}>{c.cellIsolated}</div>
            </div>
          </div>
          <div style={{ marginTop: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, padding: '16px 20px', borderTop: '1px solid var(--line)' }}>
            <span style={{ fontFamily: 'var(--mono)', fontSize: 11, fontWeight: 600, color: 'var(--ink-faint)' }}>M019</span>
            <span style={{ fontSize: 14, color: 'var(--ink-dim)', lineHeight: 1.5, textAlign: 'center' }}>{c.federation}</span>
          </div>
        </div>
      )}

      {tab === 'compile' && (
        <div>
          <h3 style={{ margin: '0 0 10px', fontFamily: 'var(--serif)', fontSize: 21, fontWeight: 600, letterSpacing: '-0.01em', color: 'var(--ink)', textAlign: 'center' }}>{c.compTitle}</h3>
          <p style={{ margin: '0 auto 28px', fontSize: 15, lineHeight: 1.65, color: 'var(--ink-dim)', maxWidth: 640, textAlign: 'center' }}>{c.compBody}</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 36, alignItems: 'start' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 22 }}>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink-dim)', border: '1px solid var(--line-strong)', padding: '8px 12px', borderRadius: 3 }}>selector-selection.json</span>
                <span style={{ color: 'var(--ink-faint)' }}>→</span>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink-dim)', border: '1px solid var(--line-strong)', padding: '8px 12px', borderRadius: 3 }}>compile --optimize</span>
                <span style={{ color: 'var(--ink-faint)' }}>→</span>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color: 'var(--ink-dim)', border: '1px solid var(--line-strong)', padding: '8px 12px', borderRadius: 3 }}>.providence/compiled/</span>
              </div>
              <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
                {c.compStats.map((s) => (
                  <div key={s.label}>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: 21, fontWeight: 600, color: s.color }}>{withGovernanceStats(stats, s.value)}</div>
                    <div style={{ fontSize: 12, color: 'var(--ink-faint)' }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </div>
            <Terminal title="sdd — compile" chrome lines={termCompileLive} />
          </div>
        </div>
      )}
    </div>
  );
}
