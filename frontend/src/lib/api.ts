import type { HistoryItem, ProfileRecord, TaxCalculationRequest, TaxResult } from '../types';

const BASE = (window.__TAX_API_BASE__ || import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');

async function request<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try { const b = await res.json(); detail = b.detail || b.error || detail; } catch {}
    throw new Error(detail);
  }
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json() as Promise<T>;
  return res.blob() as unknown as Promise<T>;
}

export const api = {
  health: () => request<any>('/api/health'),
  years: () => request<{financial_years: any[]}>('/api/tax/years'),
  rules: (fy: string) => request<any>(`/api/tax/rules/${fy}`),
  calculate: (payload: TaxCalculationRequest) => request<TaxResult>('/api/tax/calculate', { method: 'POST', body: JSON.stringify(payload) }),
  compare: (payload: TaxCalculationRequest) => request<TaxResult>('/api/tax/compare', { method: 'POST', body: JSON.stringify({ ...payload, regime: 'compare' }) }),
  exportPdf: async (payload: TaxCalculationRequest) => {
    const res = await fetch(`${BASE}/api/tax/export`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    if (!res.ok) { let d = 'Export failed'; try { const b = await res.json(); d = b.detail || d; } catch {} throw new Error(d); }
    return res.blob();
  },
  history: () => request<{items: HistoryItem[]}>('/api/tax/history'),
  historyItem: (id: string) => request<any>(`/api/tax/history/${id}`),
  deleteHistory: (id: string) => request<any>(`/api/tax/history/${id}`, { method: 'DELETE' }),
  profiles: () => request<{items: ProfileRecord[]}>('/api/profiles'),
  createProfile: (p: any) => request<ProfileRecord>('/api/profiles', { method: 'POST', body: JSON.stringify(p) }),
  updateProfile: (id: string, p: any) => request<ProfileRecord>(`/api/profiles/${id}`, { method: 'PUT', body: JSON.stringify(p) }),
  deleteProfile: (id: string) => request<any>(`/api/profiles/${id}`, { method: 'DELETE' }),
};
