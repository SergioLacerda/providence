import React from 'react';

/**
 * Providence — GovernanceFooter
 * The CLI's signature trailer line:
 *   PROVIDENCE GOVERNANCE: drift=<status> | governance=<status> | profile=<profile>
 * Status words are color-coded. Use on a dark (terminal) or light surface.
 */
export interface GovernanceFooterProps {
  drift?: string;
  governance?: string;
  profile?: string;
  surface?: 'dark' | 'light';
  style?: React.CSSProperties;
}

export function GovernanceFooter({ drift = 'clean', governance = 'active', profile = 'client', surface = 'dark', style = {} }: GovernanceFooterProps) {
  const dark = surface === 'dark';
  const palette: Record<string, string> = dark
    ? { clean: 'var(--term-green)', active: 'var(--term-green)', warn: 'var(--term-amber)', detected: 'var(--term-amber)', partial: 'var(--term-amber)', blocked: 'var(--term-red)', failed: 'var(--term-red)' }
    : { clean: 'var(--green-700)', active: 'var(--green-700)', warn: 'var(--amber-700)', detected: 'var(--amber-700)', partial: 'var(--amber-700)', blocked: 'var(--red-700)', failed: 'var(--red-700)' };
  const c = (v: string) => palette[v] || (dark ? 'var(--term-text)' : 'var(--ink-700)');

  const labelColor = dark ? 'var(--term-indigo)' : 'var(--indigo-600)';
  const sepColor = dark ? 'var(--term-dim)' : 'var(--ink-300)';
  const keyColor = dark ? 'var(--term-dim)' : 'var(--ink-500)';

  const Field = ({ k, v }: { k: string; v: string }) => (
    <>
      <span style={{ color: keyColor }}>{k}=</span>
      <span style={{ color: c(v), fontWeight: 600 }}>{v}</span>
    </>
  );

  return (
    <div
      data-governance-footer
      style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--text-xs)',
        letterSpacing: '0.01em',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 'var(--space-2)',
        padding: '8px 12px',
        borderRadius: 'var(--radius-md)',
        background: dark ? 'var(--term-panel)' : 'var(--surface-sunken)',
        border: `1px solid ${dark ? 'var(--term-border)' : 'var(--border-subtle)'}`,
        ...style,
      }}
    >
      <span style={{ color: labelColor, fontWeight: 700 }}>PROVIDENCE GOVERNANCE:</span>
      <Field k="drift" v={drift} />
      <span style={{ color: sepColor }}>|</span>
      <Field k="governance" v={governance} />
      <span style={{ color: sepColor }}>|</span>
      <Field k="profile" v={profile} />
    </div>
  );
}
