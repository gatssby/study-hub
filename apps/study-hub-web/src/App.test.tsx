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
