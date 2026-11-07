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
});
it('does not render non-finite or out-of-range progress as a real percentage', () => {
  render(<Progress label="Unknown" value={NaN} />);
  expect(screen.queryByRole('progressbar')).toBeNull();
  expect(screen.getByText('Progresso indisponível')).toBeTruthy();
});
