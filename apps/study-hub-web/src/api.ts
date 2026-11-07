export type Count = number | null;
export interface Snapshot {
  observed_at: string;
  transcription: { done: Count; queued: Count; review: Count; processing: Count; current_progress: Count };
  queue_scope?: { active: Count; archived: Count; ignored: Count };
  pdf: { materials: Count; pages: Count; released: Count; blocked: Count };
  video: { available_sources: Count; indexed_objects: Count; pending_sources: Count };
  services: Record<string, string>;
  storage: { free_bytes: Count; total_bytes: Count; study_hub_bytes?: Count; temp_bytes?: Count; whisper_reserve_bytes?: Count; growth_bytes_per_day?: Count; warning?: string | null };
  onedrive: { state: string; last_observed_at: number | null; pdf_sync?: string; transcript_sync?: string };
  transfer: { state: string };
  pace?: Partial<Record<'comparable_samples' | 'median_processing_per_audio' | 'remaining_active_audio_s' | 'unknown_duration_jobs' | 'ignored_jobs' | 'eta_seconds' | 'eta_low_seconds' | 'eta_high_seconds' | 'completed_24h' | 'audio_24h_s', Count>>;
  downloads?: { verified: Count; error: Count; unavailable: Count; other: Count; verified_bytes: Count };
  reviews?: { discipline: string; severity: string; reasons: Record<string, number>; intervals: number[][]; state: string }[];
}
export async function loadSnapshot(): Promise<Snapshot> {
  const response = await fetch('/api/dashboard', { cache: 'no-store', signal: AbortSignal.timeout(30000) });
  if (!response.ok) throw new Error('Observador indisponível');
  const value: Snapshot = await response.json();
  if (!Number.isFinite(Date.parse(value.observed_at)) || !value.transcription || !value.pdf || !value.video || !value.storage || !value.services || !value.onedrive || !value.transfer) throw new Error('Observação inválida');
  return value;
}
