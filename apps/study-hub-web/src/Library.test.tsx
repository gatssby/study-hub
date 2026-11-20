import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';

const lesson = { id: 'fo_0000000000000001', course: 'Curso 2027', subject: 'Física', module: 'Mecânica', title: 'Aula 1 — Movimento', status: 'validated', duration_s: 80 };
const review = { ...lesson, id: 'fo_0000000000000002', title: 'Aula em análise', status: 'review' };
const chemistry = { ...lesson, id: 'fo_0000000000000003', subject: 'Química', module: 'Orgânica', title: 'Moléculas e funções', status: 'queued' };
const states = ['queued', 'processing', 'review', 'unavailable', 'not_released'] as const;
const labels = ['Na fila', 'Em processamento', 'Em revisão', 'Indisponível', 'Ainda não lançada'];
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

function setup(hash: string, fetcher: (path: string) => Response) {
  window.history.replaceState(null, '', `/${hash}`);
  const fetch = vi.fn(async (path: string) => fetcher(path));
  vi.stubGlobal('fetch', fetch);
  const dashboard = vi.fn().mockRejectedValue(new Error('Unexpected dashboard fetch'));
  render(<App load={dashboard} />);
  return { fetch, dashboard };
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.history.replaceState(null, '', '/');
});

it('browses course, subject, module and lesson, then reads approved timestamps', async () => {
  const { fetch, dashboard } = setup('#/biblioteca', path => path === '/api/library'
    ? response({ lessons: [lesson, review, chemistry] })
    : response({ lesson, segments: [{ start_s: 5, end_s: 10, text: 'Texto aprovado da aula.' }] }));
  await screen.findByRole('heading', { name: 'Biblioteca' });
  const course = await screen.findByLabelText('Curso');
  await userEvent.selectOptions(course, 'Curso 2027');
  await userEvent.selectOptions(screen.getByLabelText('Disciplina'), 'Física');
  await userEvent.selectOptions(screen.getByLabelText('Módulo'), 'Mecânica');
  expect(screen.queryByText(chemistry.title)).toBeNull();
  await userEvent.click(screen.getByRole('link', { name: lesson.title }));
  await screen.findByRole('heading', { name: lesson.title });
  expect(screen.getByText('0:05–0:10')).toBeTruthy();
  expect(screen.getByText('Texto aprovado da aula.')).toBeTruthy();
  expect(fetch.mock.calls.map(([path]) => path)).toEqual(['/api/library', `/api/lessons/${lesson.id}`]);
  expect(dashboard).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('link', { name: 'Voltar à biblioteca' }));
  expect((await screen.findByLabelText<HTMLSelectElement>('Disciplina')).value).toBe('Física');
  expect(screen.queryByText('Texto aprovado da aula.')).toBeNull();
});

it('finds accent-insensitive text and combines it with a subject filter', async () => {
  setup('#/biblioteca', () => response({ lessons: [lesson, review, chemistry] }));
  const search = await screen.findByRole('searchbox', { name: 'Buscar aulas' });
  await screen.findByRole('link', { name: chemistry.title });
  await userEvent.type(search, 'moleculas');
  expect(screen.getByRole('link', { name: chemistry.title })).toBeTruthy();
  expect(screen.queryByRole('link', { name: lesson.title })).toBeNull();
  await userEvent.selectOptions(screen.getByLabelText('Disciplina'), 'Física');
  expect(screen.getByText('Nenhuma aula encontrada.')).toBeTruthy();
});

it.each(states.map((status, i) => ({ status, label: labels[i] })))('never renders segments for $status, even from an inconsistent payload', async ({ status, label }) => {
  const { fetch } = setup(`#/aulas/${lesson.id}`, () => response({
    lesson: { ...lesson, status }, segments: [{ start_s: 1, end_s: 2, text: 'PRIVATE' }],
  }));
  await screen.findByText(label);
  expect(screen.queryByText('PRIVATE')).toBeNull();
  expect(fetch.mock.calls.map(([path]) => path)).toEqual([`/api/lessons/${lesson.id}`]);
});

it('handles a missing lesson without showing old content', async () => {
  setup(`#/aulas/${lesson.id}`, () => response({}, 404));
  expect(await screen.findByText('Aula não encontrada.')).toBeTruthy();
  expect(screen.queryByRole('heading', { name: 'Transcrição' })).toBeNull();
});
