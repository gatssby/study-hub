import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';
import { Progress } from './components';

const snapshot = { observed_at: '2026-11-07T18:00:00Z', transcription: { done: 12, queued: 2999, review: 3, processing: 1, current_progress: 0.4 }, pdf: { materials: 174, pages: 8457, released: 7912, blocked: 545 }, video: { available_sources: 3001, indexed_objects: 2252, pending_sources: 14 }, services: { transcription: 'active', catalog: 'active', onedrive: 'active' }, storage: { free_bytes: 11811160064, total_bytes: 49392123904 }, onedrive: { state: 'unknown', last_observed_at: null }, transfer: { state: 'not_instrumented' } };
const load = () => Promise.resolve(snapshot);
afterEach(cleanup);

describe('Dashboard read-only', () => {
  it('uses concise sprint2 labels and keeps technical prose in advanced details', async () => {
    render(<App load={load} />);
    await screen.findByText('Transcrevendo');
    for (const label of ['Concluídas', 'Na fila', 'Revisão', 'Downloads']) {
      expect(screen.getByText(label)).toBeTruthy();
    }
    expect(screen.getByText('CC BY 4.0')).toBeTruthy();
    expect(screen.getByText(/Bytes e velocidade não instrumentados/).closest('details')).toBeTruthy();
    expect(screen.getByText(/Timer ativo não comprova/).closest('details')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /aprovar|reprocessar|excluir/i })).toBeNull();
  });
  it('renders observed counters, no invented download percentage, and accessible details', async () => {
    render(<App load={load} now={() => Date.parse('2026-11-07T18:00:10Z')} />);
    await screen.findByText('2.999');
    expect(screen.getByText('3.001 fontes disponíveis')).toBeTruthy();
    expect(screen.getByText('2.252 objetos no último índice')).toBeTruthy();
    expect(screen.getByText(/Bytes e velocidade não instrumentados/)).toBeTruthy();
    expect(screen.getByRole('progressbar', { name: 'Aula em transcrição' }).getAttribute('aria-valuenow')).toBe('40');
    await userEvent.click(screen.getByRole('button', { name: 'Detalhes de PDFs' }));
    expect(screen.getByText('545 páginas bloqueadas')).toBeTruthy();
    expect(screen.queryByText('Arjun Sharma')).toBeNull();
  });
  it('uses the observed active denominator, not archived or ignored jobs', async () => {
    render(<App load={async () => ({ ...snapshot, queue_scope: { active: 3020, archived: 519, ignored: 7 } })} />);
    await screen.findByText('3.020 no acervo ativo');
    await userEvent.click(screen.getByRole('button', { name: 'Detalhes de Transcrições' }));
    expect(screen.getByText(/Arquivados: 519/)).toBeTruthy();
    expect(screen.getByText(/Ignorados: 7/)).toBeTruthy();
  });
  it('shows loading then offline without falling back to sample data', async () => {
    let reject: (reason: Error) => void = () => {};
    render(<App load={() => new Promise((_, r) => { reject = r; })} />);
    expect(screen.getByText('Carregando observação…')).toBeTruthy();
    reject(new Error('private signed URL'));
    await screen.findByText('Sem conexão com o observador.');
    expect(screen.queryByText('private signed URL')).toBeNull();
    expect(screen.queryByText('2.999')).toBeNull();
  });
  it('marks old observations stale and unknown values unavailable, never zero', async () => {
    render(<App load={async () => ({ ...snapshot, transcription: { ...snapshot.transcription, done: null, current_progress: null } })} now={() => Date.parse('2026-11-07T19:00:00Z')} />);
    await screen.findByText(/Observação desatualizada/);
    expect(screen.queryByRole('progressbar', { name: 'Aula em transcrição' })).toBeNull();
    expect(screen.getAllByText('Indisponível').length).toBeGreaterThan(0);
  });
  it('retains the last timestamp and explicitly marks a failed refresh', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
    const loader = vi.fn().mockResolvedValueOnce(snapshot).mockRejectedValue(new Error('down'));
    render(<App load={loader} now={() => Date.parse('2026-11-07T18:00:10Z')} />);
    await screen.findByText('2.999');
    await vi.advanceTimersByTimeAsync(20000);
    await waitFor(() => expect(screen.getByText(/Falha ao atualizar/)).toBeTruthy());
    expect(screen.getByText('2.999')).toBeTruthy();
    vi.useRealTimers();
  });
  it('shows real pace, ETA range, downloads and review reasons without repeating read-only prose', async () => {
    const pace = { comparable_samples: 15, median_processing_per_audio: 2.6, remaining_active_audio_s: 5250298, unknown_duration_jobs: 4, ignored_jobs: 178, eta_seconds: 13665775, eta_low_seconds: 12000000, eta_high_seconds: 15000000, completed_24h: 8, audio_24h_s: 12801 };
    render(<App load={async () => ({ ...snapshot, pace, downloads: { verified: 2997, error: 5, unavailable: 3, other: 0, verified_bytes: 439403911772 }, reviews: [{ discipline: 'Química', severity: 'grave', reasons: { bad_timestamp: 2 }, intervals: [[2091, 2121]], state: 'review' }] })} />);
    await screen.findByText('2,6 min/min');
    expect(screen.getByText(/~158 dias/)).toBeTruthy();
    expect(screen.getByText(/139–174 dias/)).toBeTruthy();
    expect(screen.getByText('8 aulas em 24 h')).toBeTruthy();
    expect(screen.getByText('2.997 verificados')).toBeTruthy();
    expect(screen.getByText(/Química · grave · bad_timestamp ×2/)).toBeTruthy();
    expect(screen.getByText(/34:51–35:21/)).toBeTruthy();
    expect(screen.queryByText('Observação somente leitura')).toBeNull();
    expect(screen.queryByText('Somente leitura')).toBeNull();
  });
  it('renders OneDrive epoch-second observation as a real date, not 1970', async () => {
    render(<App load={async () => ({ ...snapshot, onedrive: { state: 'active', last_observed_at: 1794082879, pdf_sync: 'verified', transcript_sync: 'verified' } })} />);
    await screen.findByText(/Conclusão: .*2026/);
    expect(screen.queryByText(/1970/)).toBeNull();
  });
  it('shows Study Hub usage, temporaries and Whisper reserve in the storage card', async () => {
    render(<App load={async () => ({ ...snapshot, storage: { ...snapshot.storage, study_hub_bytes: 2486953419, temp_bytes: 140361671, whisper_reserve_bytes: 5097523696, warning: null } })} />);
    await screen.findByText('2,3 GiB Study Hub');
    expect(screen.getByText('0,1 GiB temporários')).toBeTruthy();
    expect(screen.getByText('4,7 GiB reserva Whisper')).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });
  it('withholds ETA when samples are insufficient and surfaces a real storage warning', async () => {
    render(<App load={async () => ({ ...snapshot, pace: { comparable_samples: 2, eta_seconds: null }, storage: { ...snapshot.storage, warning: 'low_reserve' } })} />);
    await screen.findByText('Sem amostra suficiente');
    expect(screen.getByRole('alert').textContent).toMatch(/abaixo da reserva do Whisper/);
  });
  it('preserves known service failures instead of labelling them unavailable', async () => {
    render(<App load={async () => ({ ...snapshot, services: { ...snapshot.services, materials: 'failed', catalog: 'activating' } })} />);
    await screen.findByText('Materiais: falhou');
    expect(screen.getByText('Catálogo: iniciando')).toBeTruthy();
  });
  it('shows the last approval and distinguishes a scheduled collector from a running one', async () => {
    const last = 1794074400;
    render(<App load={async () => ({ ...snapshot, transcription: { ...snapshot.transcription, last_validated_at: last }, services: { ...snapshot.services, materials: 'scheduled' } })} now={() => Date.parse('2026-11-07T18:30:00Z')} />);
    await screen.findByText((content) => content.startsWith(`Última transcrição aprovada: ${new Date(last * 1000).toLocaleString('pt-BR')}`));
    expect(screen.getByText(/há \d+ (min|h|d)/)).toBeTruthy();
    expect(screen.getByText('Materiais: agendado')).toBeTruthy();
  });
  it('surfaces operational health alerts prominently and review severity totals', async () => {
    render(<App load={async () => ({ ...snapshot,
      health: { observed_at: 1794074400, alerts: ['breaker_open', 'onedrive_stale'], breaker_open: true, leased: 0, phase_age_s: null, last_finished_age_s: 90000, eligible_queued: 2700, materials_fail_streak: 0, onedrive_age_s: 12000, active_deferrals: 13, persistent_deferrals: 0 },
      review_counts: { total: 46, grave: 45, leve: 0, desconhecida: 1 },
      reassessment: { validated: 2, review: 40, error: 1 } })} />);
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toMatch(/Disjuntor da transcrição aberto/);
    expect(alert.textContent).toMatch(/OneDrive desatualizada/);
    await userEvent.click(screen.getByRole('button', { name: 'Detalhes de Transcrições' }));
    expect(screen.getByText(/45 graves/)).toBeTruthy();
    expect(screen.getByText(/Reavaliação automática: 2 publicadas · 40 mantidas · 1 erro/)).toBeTruthy();
  });
  it('does not invent health alerts when the health snapshot is unknown', async () => {
    render(<App load={async () => ({ ...snapshot, health: { observed_at: null, alerts: null } })} />);
    await screen.findByText('Transcrevendo');
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
it('does not render non-finite or out-of-range progress as a real percentage', () => {
  render(<Progress label="Unknown" value={NaN} />);
  expect(screen.queryByRole('progressbar')).toBeNull();
  expect(screen.getByText('Progresso indisponível')).toBeTruthy();
});
