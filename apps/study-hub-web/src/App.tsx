import { useEffect, useState } from 'react';
import { BookOpen, Calendar, Cloud, GraduationCap, HardDrive, TrendingUp } from 'lucide-react';
import { loadSnapshot } from './api';
import type { Count, Snapshot } from './api';
import { MetricCard, Progress, Summary } from './components';

const format = (n: Count | undefined) => typeof n === 'number' && Number.isFinite(n) && n >= 0 ? n.toLocaleString('pt-BR') : 'Indisponível';
const ratio = (n: Count | undefined, d: Count | undefined) => typeof n === 'number' && typeof d === 'number' && d > 0 ? n / d : null;
const gib = (n: Count | undefined) => typeof n === 'number' && Number.isFinite(n) && n >= 0 ? `${(n / 1024 ** 3).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} GiB` : 'Indisponível';
const days = (s: Count | undefined) => typeof s === 'number' && Number.isFinite(s) && s >= 0 ? Math.round(s / 86400) : null;
const clockTime = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
const labels: Record<string, string> = { transcription: 'Transcrição', catalog: 'Catálogo', materials: 'Materiais', videos: 'Vídeos', index: 'Índice', onedrive: 'OneDrive', ocr: 'OCR' };
const serviceStates: Record<string, string> = { active: 'ativo', inactive: 'inativo', failed: 'falhou', activating: 'iniciando', deactivating: 'encerrando', reloading: 'recarregando' };
const syncStates: Record<string, string> = { verified: 'verificado', failed: 'falhou', absent: 'ausente', not_generated: 'não gerado' };
const syncState = (value: string | undefined) => syncStates[value ?? ''] ?? 'Indisponível';
const serviceState = (value: string | undefined) => value ? serviceStates[value] ?? 'Indisponível' : 'Indisponível';

export function App({ load = loadSnapshot, now = Date.now }: { load?: () => Promise<Snapshot>; now?: () => number }) {
  const [data, setData] = useState<Snapshot | null>(null);
  const [error, setError] = useState(false);
  const [clock, setClock] = useState(now);
  useEffect(() => {
    let cancelled = false;
    let pending = false;
    async function refresh() {
      setClock(now());
      if (pending) return;
      pending = true;
      try { const value = await load(); if (!cancelled) { setData(value); setError(false); } }
      catch { if (!cancelled) setError(true); }
      finally { pending = false; }
    }
    void refresh();
    const interval = setInterval(() => { void refresh(); }, 20000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [load, now]);
  const stale = data !== null && (!Number.isFinite(Date.parse(data.observed_at)) || clock - Date.parse(data.observed_at) > 60000);
  const t = data?.transcription;
  const p = data?.pace;
  const eta = days(p?.eta_seconds);
  const reviews = data?.reviews ?? [];
  const current = t?.current_progress;
  const validProgress = typeof current === 'number' && Number.isFinite(current) && current >= 0 && current <= 1;
  const total = data?.queue_scope ? data.queue_scope.active : t && [t.done, t.queued, t.review, t.processing].every(n => typeof n === 'number' && Number.isFinite(n) && n >= 0) ? t.done! + t.queued! + t.review! + t.processing! : null;
  const stamp = data ? new Date(data.observed_at).toLocaleString('pt-BR') : null;
  return <main className="page"><div className="container">
    <header className="app-header"><div><h1>Seu Study Hub 👋</h1><p className="secondary subtitle">Federal Online • Visão geral • {stamp ? `Observado em ${stamp}` : 'Seu acervo de estudos'}</p></div><span className="badge"><GraduationCap size={14} /> Federal Online</span></header>
    <p role="status" className="observation small secondary">{!data ? (error ? 'Sem conexão com o observador.' : 'Carregando observação…') : error ? 'Falha ao atualizar — exibindo a última observação.' : stale ? 'Observação desatualizada — confira o horário antes de usar os dados.' : 'Observação disponível • atualização a cada 20 segundos'}</p>
    {data?.storage.warning ? <p role="alert" className="observation small">{data.storage.warning === 'low_reserve' ? 'Espaço livre abaixo da reserva do Whisper.' : 'Crescimento recente esgota a reserva em até 7 dias.'}</p> : null}
    <section className="summaries" aria-label="Resumo da transcrição">
      <Summary label="Transcrevendo" value={validProgress ? `${format(Math.round(current * 1000) / 10)}%` : 'Indisponível'} note={<Progress label="Aula em transcrição" value={current ?? null} small />} icon={<Calendar className="blue" />} />
      <Summary label="Concluídas" value={format(t?.done)} note="Transcrições aprovadas" icon={<TrendingUp className="green" />} />
      <Summary label="Na fila" value={format(t?.queued)} note="Aguardando processamento" icon={<BookOpen className="purple" />} />
      <Summary label="Revisão" value={format(t?.review)} note="Aguardando validação" icon={<GraduationCap className="orange" />} />
    </section>
    <section aria-labelledby="overview-title"><div className="section-heading"><h2 id="overview-title">Seu acervo 📚</h2><span className="badge small">Sistema</span></div>
      <div className="metrics">
        <MetricCard title="Transcrições" badge="QA ativa" tone="tile-blue" icon={<BookOpen />} detail={<><p>{format(t?.processing)} aula(s) em processamento</p><p>{format(t?.review)} revisão(ões) privada(s). Nenhum texto em revisão é exposto.</p><p>O progresso da aula é o último checkpoint durável, não tempo estimado.</p><p>Ativos: {format(data?.queue_scope?.active)} · Arquivados: {format(data?.queue_scope?.archived)} · Ignorados: {format(data?.queue_scope?.ignored)}</p><p>Ritmo: mediana do tempo total por minuto de áudio em {format(p?.comparable_samples)} aulas comparáveis (exclui pilotos &lt;5 min e reuso de cache). Faixa = quartis 25–75%. Inglês/Espanhol fora da previsão ({format(p?.ignored_jobs)} jobs).</p>{p?.unknown_duration_jobs ? <p>{format(p.unknown_duration_jobs)} job(s) sem duração no catálogo fora da estimativa.</p> : null}{reviews.length ? <ul className="micro">{reviews.map((r, i) => <li key={i}>{r.discipline} · {r.severity} · {Object.entries(r.reasons).map(([k, v]) => `${k} ×${v}`).join(', ') || 'sem motivo classificado'}{r.intervals.length ? ` · ${r.intervals.map(([a, b]) => `${clockTime(a)}–${clockTime(b)}`).join(', ')}` : ''}</li>)}</ul> : null}</>}>
          <div className="facts"><p>{typeof p?.median_processing_per_audio === 'number' ? `${p.median_processing_per_audio.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} min/min` : 'Ritmo indisponível'}</p><p>{eta === null ? 'Sem amostra suficiente' : `~${eta} dias`}</p><p>{days(p?.eta_low_seconds) !== null && days(p?.eta_high_seconds) !== null && eta !== null ? `${days(p?.eta_low_seconds)}–${days(p?.eta_high_seconds)} dias` : '—'}</p><p>{format(p?.completed_24h)} aulas em 24 h</p></div>
          <div className="facts"><p>{format(t?.done)} aprovadas</p><p>{format(total)} no acervo ativo</p><p>{format(t?.queued)} na fila</p><p>{format(t?.review)} em revisão</p></div><div className="progress-caption small"><span>Transcrições aprovadas</span><span>{total ? `${format(Math.round((t!.done! / total) * 1000) / 10)}%` : 'Indisponível'}</span></div><Progress label="Transcrições aprovadas" value={ratio(t?.done, total)} /><div className="micro muted split"><span>Acervo ativo</span><span>Versões atuais</span></div>
        </MetricCard>
        <MetricCard title="PDFs" badge="Privacidade" tone="tile-green" icon={<BookOpen />} detail={<><p>{format(data?.pdf.blocked)} páginas bloqueadas</p><p>OCR em revisão e originais privados não são disponibilizados. Liberação não certifica a integridade acadêmica de fórmulas e figuras.</p></>}>
          <div className="facts"><p>{format(data?.pdf.materials)} materiais indexados</p><p>{format(data?.pdf.pages)} páginas</p><p>{format(data?.pdf.released)} páginas liberadas</p><p>{format(data?.pdf.blocked)} em revisão</p></div><div className="progress-caption small"><span>Páginas liberadas</span><span>{data?.pdf.pages && data.pdf.released !== null ? `${format(Math.round(data.pdf.released / data.pdf.pages * 1000) / 10)}%` : 'Indisponível'}</span></div><Progress label="Páginas PDF liberadas" value={ratio(data?.pdf.released, data?.pdf.pages)} /><div className="micro muted split"><span>Texto consultável</span><span>Originais privados</span></div>
        </MetricCard>
        <MetricCard title="Downloads" badge="Disponibilidade" tone="tile-purple" icon={<BookOpen />} detail={<><p>Fontes, jobs e objetos de vídeo têm grãos diferentes. Esses totais não medem a proporção de downloads concluídos.</p><p>Bytes e velocidade não instrumentados. Progresso de download indisponível.</p></>}>
          <div className="facts"><p>{format(data?.video.available_sources)} fontes disponíveis</p><p>{format(data?.video.indexed_objects)} objetos no último índice</p><p>{format(data?.downloads?.verified)} verificados</p></div><div className="micro muted split"><span>{format(data?.downloads?.error)} com erro</span><span>{format(data?.downloads?.unavailable)} indisponíveis</span></div>
        </MetricCard>
        <MetricCard title="OneDrive" badge="Sincronização" tone="tile-orange" icon={<Cloud />} detail={<p>Timer ativo não comprova sincronização concluída. O estado abaixo só indica o produtor observado; byte check e conclusão exigem telemetria própria.</p>}>
          <div className="facts"><p>Unidade: {serviceState(data?.onedrive.state)}</p><p>PDFs: {syncState(data?.onedrive.pdf_sync)}</p><p>Conclusão: {typeof data?.onedrive.last_observed_at === 'number' ? new Date(data.onedrive.last_observed_at * 1000).toLocaleString('pt-BR') : 'Indisponível'}</p><p>Verificação: {syncState(data?.onedrive.transcript_sync)}</p></div>
        </MetricCard>
        <MetricCard title="Armazenamento" badge="VPS" tone="tile-red" icon={<HardDrive />} detail={<p>Alerta só quando o livre fica abaixo da reserva do Whisper ou o crescimento recente (≥6 h de amostras) a esgota em até 7 dias. Nenhuma limpeza automática. Crescimento: {data?.storage.growth_bytes_per_day == null ? 'amostras insuficientes' : `${gib(data.storage.growth_bytes_per_day)}/dia`}.</p>}>
          <div className="facts"><p>{gib(data?.storage.free_bytes)} livres</p><p>{gib(data?.storage.total_bytes)} totais</p><p>{gib(data?.storage.study_hub_bytes)} Study Hub</p><p>{gib(data?.storage.temp_bytes)} temporários</p><p>{gib(data?.storage.whisper_reserve_bytes)} reserva Whisper</p></div><div className="progress-caption small"><span>Espaço livre na VPS</span></div><Progress label="Espaço livre na VPS" value={ratio(data?.storage.free_bytes, data?.storage.total_bytes)} />
        </MetricCard>
      </div>
    </section>
    <details className="card services"><summary>Detalhes avançados</summary><h2 id="services-title">Serviços observados</h2><div className="service-list">{Object.entries(labels).map(([key, label]) => <span className="badge" key={key}>{label}: {serviceState(data?.services[key])}</span>)}</div><p className="micro muted">Saúde observacional dos serviços FO; timer ativo não é prova de última execução bem-sucedida.</p></details>
    <footer className="micro muted">Adaptado de <a href="https://www.figma.com/community/file/1531598093643920564/student-dashboard-lms-application" target="_blank" rel="noreferrer">Student Dashboard LMS Application — Sakshi Parashar</a>, <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">CC BY 4.0</a>. Conteúdo e integração modificados para Study Hub.</footer>
  </div></main>;
}
