export type Count = number | null;
export interface Snapshot {
  observed_at: string;
  transcription: { done: Count; queued: Count; review: Count; processing: Count; current_progress: Count };
  pdf: { materials: Count; pages: Count; released: Count; blocked: Count };
  video: { available_sources: Count; indexed_objects: Count; pending_sources: Count };
  services: Record<string, string>;
  storage: { free_bytes: Count; total_bytes: Count };
  onedrive: { state: string; last_observed_at: string | null };
  transfer: { state: string };
}
export async function loadSnapshot(): Promise<Snapshot> {
  const response = await fetch('/api/dashboard', { cache: 'no-store', signal: AbortSignal.timeout(30000) });
  if (!response.ok) throw new Error('Observador indisponível');
  const value: Snapshot = await response.json();
  if (!Number.isFinite(Date.parse(value.observed_at)) || !value.transcription || !value.pdf || !value.video || !value.storage || !value.services || !value.onedrive || !value.transfer) throw new Error('Observação inválida');
  return value;
}
