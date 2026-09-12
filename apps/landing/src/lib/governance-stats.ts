/**
 * Client-safe types and formatting helpers for governance stats. No Node
 * built-ins here — this module is imported by client-hydrated React islands
 * (RuntimeProof, CapabilitiesPanel) and gets bundled for the browser.
 * Reading the real stats from `.providence/metadata.json` happens server-side only,
 * in `governance-data.server.ts`, and is passed down as a prop.
 */

export interface GovernanceStats {
  mandatesCount: number;
  guidelinesCount: number;
  /** Shortened form of the combined governance fingerprint, e.g. "f95a…901a84b2". */
  fingerprintShort: string;
  available: boolean;
}

export const PLACEHOLDER_GOVERNANCE_STATS: GovernanceStats = {
  mandatesCount: 0,
  guidelinesCount: 0,
  fingerprintShort: '—',
  available: false,
};

/**
 * Replaces `{{FP}}`, `{{MCOUNT}}`, `{{GCOUNT}}` tokens with real governance
 * stats. Counts are zero-padded to match the repo's own id scheme (M001,
 * G01) since they're only ever used to render an id range like "M001–M016".
 */
export function withGovernanceStats(stats: GovernanceStats, text: string): string {
  return text
    .replaceAll('{{FP}}', stats.fingerprintShort)
    .replaceAll('{{MCOUNT}}', String(stats.mandatesCount).padStart(3, '0'))
    .replaceAll('{{GCOUNT}}', String(stats.guidelinesCount).padStart(2, '0'));
}
