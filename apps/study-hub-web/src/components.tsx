import type { ReactNode } from 'react';
import { ChevronRight, FileText } from 'lucide-react';

export function Progress({ label, value, small = false }: { label: string; value: number | null; small?: boolean }) {
  if (value === null || !Number.isFinite(value) || value < 0 || value > 1) return <span className="muted micro">Progresso indisponível</span>;
  const percent = Math.round(value * 1000) / 10;
  return <div className={`progress ${small ? 'progress-small' : ''}`} role="progressbar" aria-label={label} aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${percent}%` }} /></div>;
}

export function Summary({ label, value, note, icon }: { label: string; value: ReactNode; note: ReactNode; icon: ReactNode }) {
  return <article className="card summary"><div><p className="secondary small">{label}</p><p className="summary-value">{value}</p><div className="muted micro">{note}</div></div>{icon}</article>;
}

export function MetricCard({ title, badge, tone, icon, children, detail }: { title: string; badge: string; tone: string; icon: ReactNode; children: ReactNode; detail: ReactNode }) {
  return <article className="card metric-card"><header className="card-header"><div className="card-heading"><span className={`icon-tile ${tone}`}>{icon}</span><div><h3>{title}</h3><p className="secondary small">Observação somente leitura</p></div></div><span className="badge">{badge}</span></header><div className="card-content">{children}<details><summary role="button" aria-label={`Detalhes de ${title}`}><FileText size={14} aria-hidden="true" />Ver detalhes<ChevronRight size={14} aria-hidden="true" /></summary><div className="detail small">{detail}</div></details></div></article>;
}
