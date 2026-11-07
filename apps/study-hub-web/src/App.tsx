import { useEffect, useState } from 'react';
import { BookOpen, Calendar, Cloud, GraduationCap, HardDrive, TrendingUp } from 'lucide-react';
import { loadSnapshot } from './api';
import type { Count, Snapshot } from './api';
import { MetricCard, Progress, Summary } from './components';

const format = (n: Count | undefined) => typeof n === 'number' && Number.isFinite(n) && n >= 0 ? n.toLocaleString('pt-BR') : 'Indisponível';
const ratio = (n: Count | undefined, d: Count | undefined) => typeof n === 'number' && typeof d === 'number' && d > 0 ? n / d : null;
const gib = (n: Count | undefined) => typeof n === 'number' && Number.isFinite(n) && n >= 0 ? `${(n / 1024 ** 3).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} GiB` : 'Indisponível';
const labels: Record<string, string> = { transcription: 'Transcrição', catalog: 'Catálogo', materials: 'Materiais', videos: 'Vídeos', index: 'Índice', onedrive: 'OneDrive', ocr: 'OCR' };
const serviceStates: Record<string, string> = { active: 'ativo', inactive: 'inativo', failed: 'falhou', activating: 'iniciando', deactivating: 'encerrando', reloading: 'recarregando' };
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
  const current = t?.current_progress;
  const validProgress = typeof current === 'number' && Number.isFinite(current) && current >= 0 && current <= 1;
  const total = t && [t.done, t.queued, t.review, t.processing].every(n => typeof n === 'number' && Number.isFinite(n) && n >= 0) ? t.done! + t.queued! + t.review! + t.processing! : null;
  const stamp = data ? new Date(data.observed_at).toLocaleString('pt-BR') : null;
  return <main className="page"><div className="container">
    <header className="app-header"><div><h1>Seu Study Hub 👋</h1><p className="secondary subtitle">Federal Online • Visão geral • {stamp ? `Observado em ${stamp}` : 'Seu acervo de estudos'}</p></div><span className="badge"><GraduationCap size={14} /> Somente leitura</span></header>
    <p role="status" className="observation small secondary">{!data ? (error ? 'Sem conexão com o observador.' : 'Carregando observação…') : error ? 'Falha ao atualizar — exibindo a última observação.' : stale ? 'Observação desatualizada — confira o horário antes de usar os dados.' : 'Observação disponível • atualização a cada 20 segundos'}</p>
    <section className="summaries" aria-label="Resumo da transcrição">
      <Summary label="Aula em transcrição" value={validProgress ? `${format(Math.round(current * 1000) / 10)}%` : 'Indisponível'} note={<Progress label="Aula em transcrição" value={current ?? null} small />} icon={<Calendar className="blue" />} />
      <Summary label="Aulas concluídas" value={format(t?.done)} note="Transcrições aprovadas" icon={<TrendingUp className="green" />} />
      <Summary label="Fila de transcrição" value={format(t?.queued)} note="Aguardando processamento" icon={<BookOpen className="purple" />} />
      <Summary label="Revisões pendentes" value={format(t?.review)} note="Conteúdo privado bloqueado" icon={<GraduationCap className="orange" />} />
    </section>
    <section aria-labelledby="overview-title"><div className="section-heading"><h2 id="overview-title">Seu acervo 📚</h2><span className="badge small">Visão geral operacional</span></div><p className="section-description small secondary">Acompanhe transcrições, materiais e disponibilidade com observações reais, sem alterar os serviços.</p>
      <div className="metrics">
        <MetricCard title="Transcrições" badge="QA ativa" tone="tile-blue" icon={<BookOpen />} detail={<><p>{format(t?.processing)} aula(s) em processamento</p><p>{format(t?.review)} revisão(ões) privada(s). Nenhum texto em revisão é exposto.</p><p>O progresso da aula é o último checkpoint durável, não tempo estimado.</p></>}>
          <div className="facts"><p>{format(t?.done)} aprovadas</p><p>{format(total)} jobs atuais</p><p>{format(t?.queued)} na fila</p><p>{format(t?.review)} em revisão</p></div><div className="progress-caption small"><span>Transcrições aprovadas</span><span>{total ? `${format(Math.round((t!.done! / total) * 1000) / 10)}%` : 'Indisponível'}</span></div><Progress label="Transcrições aprovadas" value={ratio(t?.done, total)} /><div className="micro muted split"><span>Jobs atuais, sem superseded</span><span>Versões ativas</span></div>
        </MetricCard>
        <MetricCard title="PDFs" badge="Privacidade" tone="tile-green" icon={<BookOpen />} detail={<><p>{format(data?.pdf.blocked)} páginas bloqueadas</p><p>OCR em revisão e originais privados não são disponibilizados. Liberação não certifica a integridade acadêmica de fórmulas e figuras.</p></>}>
          <div className="facts"><p>{format(data?.pdf.materials)} materiais indexados</p><p>{format(data?.pdf.pages)} páginas</p><p>{format(data?.pdf.released)} páginas liberadas</p><p>Saneamento obrigatório</p></div><div className="progress-caption small"><span>Páginas liberadas</span><span>{data?.pdf.pages && data.pdf.released !== null ? `${format(Math.round(data.pdf.released / data.pdf.pages * 1000) / 10)}%` : 'Indisponível'}</span></div><Progress label="Páginas PDF liberadas" value={ratio(data?.pdf.released, data?.pdf.pages)} /><div className="micro muted split"><span>Texto consultável</span><span>Originais privados</span></div>
        </MetricCard>
        <MetricCard title="Vídeos" badge="Disponibilidade" tone="tile-purple" icon={<BookOpen />} detail={<p>Fontes, jobs e objetos de vídeo têm grãos diferentes. Esses totais não medem a proporção de downloads concluídos.</p>}>
          <div className="facts"><p>{format(data?.video.available_sources)} fontes disponíveis</p><p>{format(data?.video.indexed_objects)} objetos no último índice</p><p>{format(data?.video.pending_sources)} fontes pendentes</p><p>URLs privadas protegidas</p></div><p className="small secondary transfer-note">Bytes e velocidade não instrumentados. Progresso de download indisponível.</p>
        </MetricCard>
        <MetricCard title="OneDrive" badge="Sincronização" tone="tile-orange" icon={<Cloud />} detail={<p>Timer ativo não comprova sincronização concluída. O estado abaixo só indica o produtor observado; byte check e conclusão exigem telemetria própria.</p>}>
          <div className="facts"><p>Unidade: {serviceState(data?.onedrive.state)}</p><p>Timer: {serviceState(data?.services.onedrive)}</p><p>Conclusão: {data?.onedrive.last_observed_at ? new Date(data.onedrive.last_observed_at).toLocaleString('pt-BR') : 'Indisponível'}</p><p>Sem arquivos privados</p></div><p className="small secondary transfer-note">Sem porcentagem de transferência: bytes ainda não instrumentados.</p>
        </MetricCard>
        <MetricCard title="Armazenamento" badge="VPS" tone="tile-red" icon={<HardDrive />} detail={<p>A consulta mede espaço livre no filesystem da VPS; não mede capacidade nem progresso do OneDrive.</p>}>
          <div className="facts"><p>{gib(data?.storage.free_bytes)} livres</p><p>{gib(data?.storage.total_bytes)} totais</p><p>Temporários compartilhados</p><p>Sem limpeza automática</p></div><div className="progress-caption small"><span>Espaço livre na VPS</span></div><Progress label="Espaço livre na VPS" value={ratio(data?.storage.free_bytes, data?.storage.total_bytes)} />
        </MetricCard>
      </div>
    </section>
    <section className="card services" aria-labelledby="services-title"><h2 id="services-title">Serviços observados</h2><div className="service-list">{Object.entries(labels).map(([key, label]) => <span className="badge" key={key}>{label}: {serviceState(data?.services[key])}</span>)}</div><p className="micro muted">Saúde observacional dos serviços FO; timer ativo não é prova de última execução bem-sucedida.</p></section>
    <footer className="micro muted">Adaptado de <a href="https://www.figma.com/community/file/1531598093643920564/student-dashboard-lms-application" target="_blank" rel="noreferrer">Student Dashboard LMS Application — Sakshi Parashar</a>, <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">CC BY 4.0</a>. Conteúdo e integração modificados para Study Hub.</footer>
  </div></main>;
}
