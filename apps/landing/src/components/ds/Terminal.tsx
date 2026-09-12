import React from 'react';

/**
 * Providence — Terminal
 * The CLI surface. Dark navy panel with a traffic-light header and a
 * monospace body. Render children, or pass `lines` for token-colored output.
 */
export type TerminalTone = 'text' | 'dim' | 'green' | 'blue' | 'amber' | 'red' | 'indigo';

export interface TerminalLine {
  prompt?: string;
  text: string;
  tone?: TerminalTone;
}

export interface TerminalProps {
  title?: string;
  lines?: TerminalLine[] | null;
  children?: React.ReactNode;
  chrome?: boolean;
  style?: React.CSSProperties;
}

export function Terminal({ title = 'sdd', lines = null, children, chrome = true, style = {} }: TerminalProps) {
  const toneColor: Record<TerminalTone, string> = {
    text: 'var(--term-text)',
    dim: 'var(--term-dim)',
    green: 'var(--term-green)',
    blue: 'var(--term-blue)',
    amber: 'var(--term-amber)',
    red: 'var(--term-red)',
    indigo: 'var(--term-indigo)',
  };
  return (
    <div
      style={{
        background: 'var(--term-bg)',
        border: '1px solid var(--term-border)',
        borderRadius: 'var(--radius-lg)',
        overflow: 'hidden',
        boxShadow: 'var(--shadow-lg)',
        ...style,
      }}
    >
      {chrome && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)',
            padding: '10px 14px',
            borderBottom: '1px solid var(--term-border)',
            background: 'var(--term-panel)',
          }}
        >
          <span style={{ width: 11, height: 11, borderRadius: '50%', background: '#ff5f57' }} />
          <span style={{ width: 11, height: 11, borderRadius: '50%', background: '#febc2e' }} />
          <span style={{ width: 11, height: 11, borderRadius: '50%', background: '#28c840' }} />
          <span style={{ marginLeft: 'var(--space-2)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--term-dim)' }}>{title}</span>
        </div>
      )}
      <div
        style={{
          padding: '14px 16px',
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--text-sm)',
          lineHeight: 1.7,
          color: 'var(--term-text)',
          whiteSpace: 'pre-wrap',
          overflowX: 'auto',
        }}
      >
        {lines
          ? lines.map((ln, i) => (
              <div key={i}>
                {ln.prompt && <span style={{ color: 'var(--term-dim)' }}>{ln.prompt} </span>}
                <span style={{ color: toneColor[ln.tone || 'text'] }}>{ln.text}</span>
              </div>
            ))
          : children}
      </div>
    </div>
  );
}
