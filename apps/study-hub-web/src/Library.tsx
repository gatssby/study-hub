import { useEffect, useMemo, useRef, useState } from 'react';
import { BookOpen, GraduationCap } from 'lucide-react';
import { loadLesson, loadLibrary } from './api';
import type { LessonDetail, LessonMetadata, LessonStatus } from './api';

const statuses: Record<LessonStatus, { label: string; note: string }> = {
  validated: { label: 'Validada', note: '' },
  queued: { label: 'Na fila', note: 'Aguardando processamento.' },
  processing: { label: 'Em processamento', note: 'A transcrição desta aula está sendo processada.' },
  review: { label: 'Em revisão', note: 'A transcrição só aparece após a validação.' },
  unavailable: { label: 'Indisponível', note: 'Não há transcrição disponível para esta aula.' },
  not_released: { label: 'Ainda não lançada', note: 'Esta aula ainda não foi lançada no catálogo de origem.' },
};
const collator = new Intl.Collator('pt-BR', { numeric: true, sensitivity: 'base' });
const sort = (a: string, b: string) => collator.compare(a, b);
const options = (rows: LessonMetadata[], key: 'course' | 'subject' | 'module') => [...new Set(rows.map(row => row[key]))].sort(sort);
const fold = (value: string) => value.normalize('NFD').replace(/\p{M}/gu, '').toLocaleLowerCase('pt-BR');
const pageSize = 50;

function clock(seconds: number) {
  const whole = Math.floor(seconds);
  const mm = Math.floor(whole / 60);
  const ss = String(whole % 60).padStart(2, '0');
  return mm >= 60 ? `${Math.floor(mm / 60)}:${String(mm % 60).padStart(2, '0')}:${ss}` : `${mm}:${ss}`;
}

function Status({ value }: { value: LessonStatus }) {
  return <span className={`badge lesson-status status-${value}`}>{statuses[value].label}</span>;
}

function LibraryBrowse({ hidden }: { hidden: boolean }) {
  const [lessons, setLessons] = useState<LessonMetadata[] | null>(null);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState('');
  const [course, setCourse] = useState('');
  const [subject, setSubject] = useState('');
  const [module, setModule] = useState('');
  const [visible, setVisible] = useState(pageSize);
  useEffect(() => {
    const controller = new AbortController();
    void loadLibrary(controller.signal).then(setLessons, () => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, []);
  const indexed = useMemo(() => (lessons ?? []).map(row => ({
    row, searchable: fold(`${row.course} ${row.subject} ${row.module} ${row.title}`),
  })).sort(({ row: a }, { row: b }) => sort(a.course, b.course) || sort(a.subject, b.subject) || sort(a.module, b.module) || sort(a.title, b.title)), [lessons]);
  const byCourse = (lessons ?? []).filter(row => !course || row.course === course);
  const bySubject = byCourse.filter(row => !subject || row.subject === subject);
  const terms = fold(query).trim().split(/\s+/).filter(Boolean);
  const matches = indexed.filter(({ row, searchable }) => (!course || row.course === course)
    && (!subject || row.subject === subject) && (!module || row.module === module)
    && terms.every(term => searchable.includes(term)));

  return <section hidden={hidden} aria-label="Catálogo de aulas" className="card library-card">
    <div className="library-filters">
      <label>Buscar aulas<input type="search" maxLength={160} value={query} onChange={event => { setQuery(event.target.value); setVisible(pageSize); }} placeholder="Título, disciplina ou módulo" /></label>
      <label>Curso<select value={course} onChange={event => { setCourse(event.target.value); setSubject(''); setModule(''); setVisible(pageSize); }}>
        <option value="">Todos os cursos</option>{options(lessons ?? [], 'course').map(value => <option key={value}>{value}</option>)}
      </select></label>
      <label>Disciplina<select value={subject} onChange={event => { setSubject(event.target.value); setModule(''); setVisible(pageSize); }}>
        <option value="">Todas as disciplinas</option>{options(byCourse, 'subject').map(value => <option key={value}>{value}</option>)}
      </select></label>
      <label>Módulo<select value={module} onChange={event => { setModule(event.target.value); setVisible(pageSize); }}>
        <option value="">Todos os módulos</option>{options(bySubject, 'module').map(value => <option key={value}>{value}</option>)}
      </select></label>
    </div>
    {error ? <p role="alert">Não foi possível carregar a biblioteca. Atualize a página para tentar novamente.</p> :
      !lessons ? <p role="status">Carregando biblioteca…</p> : !matches.length ? <p role="status">Nenhuma aula encontrada.</p> : <>
        <p className="small secondary" role="status">{matches.length.toLocaleString('pt-BR')} {matches.length === 1 ? 'aula encontrada' : 'aulas encontradas'}</p>
        <ul className="lesson-list">{matches.slice(0, visible).map(({ row }) => <li key={row.id}>
          <div><a href={`#/aulas/${row.id}`}>{row.title}</a><p className="small secondary">{row.course} · {row.subject} · {row.module}</p></div>
          <Status value={row.status} />
        </li>)}</ul>
        {matches.length > visible && <button className="library-more" onClick={() => setVisible(visible + pageSize)}>Mostrar mais aulas</button>}
      </>}
  </section>;
}

function LessonView({ id }: { id: string }) {
  const [data, setData] = useState<LessonDetail | null | undefined>(undefined);
  const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void loadLesson(id, controller.signal).then(setData, () => { if (!controller.signal.aborted) setError(true); });
    return () => controller.abort();
  }, [id]);
  return <>
    <p><a className="study-link" href="#/biblioteca">Voltar à biblioteca</a></p>
    {error ? <p role="alert">Não foi possível carregar a aula. Atualize a página para tentar novamente.</p> :
      data === undefined ? <p role="status">Carregando aula…</p> : data === null ? <p role="status">Aula não encontrada.</p> : <>
        <section className="card library-card" aria-labelledby="lesson-title">
          <p className="small secondary">{data.lesson.course} · {data.lesson.subject} · {data.lesson.module}</p>
          <h2 id="lesson-title">{data.lesson.title}</h2>
          <div className="lesson-meta"><Status value={data.lesson.status} />{data.lesson.duration_s !== null &&
            <span className="small secondary">Duração: {clock(data.lesson.duration_s)}</span>}</div>
          {data.lesson.status !== 'validated' && <p className="secondary">{statuses[data.lesson.status].note}</p>}
        </section>
        {data.lesson.status === 'validated' && <article className="card library-card" aria-labelledby="transcript-title">
          <h2 id="transcript-title">Transcrição</h2>
          <ol className="transcript">{data.segments.map(({ start_s, end_s, text }, index) => <li key={index}>
            <span className="small secondary timestamp">{clock(start_s)}–{clock(end_s)}</span><p>{text}</p>
          </li>)}</ol>
        </article>}
      </>}
  </>;
}

export function Library({ lessonId }: { lessonId?: string }) {
  const [visited, setVisited] = useState(!lessonId);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (!lessonId) setVisited(true);
    heading.current?.focus();
  }, [lessonId]);
  return <main className="page"><div className="container">
    <header className="app-header"><div><h1 ref={heading} tabIndex={-1}>{lessonId ? 'Aula' : 'Biblioteca'}</h1>
      <p className="secondary subtitle">{lessonId ? 'Seu acervo de estudos' : 'Encontre aulas e leia as transcrições validadas.'}</p></div>
      <span className="badge"><GraduationCap size={14} /> Federal Online</span>
    </header>
    <nav className="study-nav" aria-label="Study Hub"><a className="study-link" href="#/biblioteca" aria-current={!lessonId ? 'page' : undefined}><BookOpen size={14} /> Biblioteca</a>
      <a className="study-link" href="#/painel">Painel</a></nav>
    {(visited || !lessonId) && <LibraryBrowse hidden={!!lessonId} />}
    {lessonId && <LessonView key={lessonId} id={lessonId} />}
  </div></main>;
}
