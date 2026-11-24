import { useEffect, useMemo, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';
import {
  Calculator, Moon, Sun, IndianRupee, TrendingDown, FileDown, Save, History, User,
  RotateCcw, ChevronDown, ChevronUp, Plus, Trash2, Info, CheckCircle2, Building2, Briefcase, Landmark, LineChart, Wallet, ReceiptText
} from 'lucide-react';
import { api } from './lib/api';
import { defaultRequest } from './lib/defaults';
import { inr, pct } from './lib/format';
import type { CapitalGainEntry, ProfileRecord, TaxCalculationRequest, TaxResult, HistoryItem } from './types';

type Tab = 'dashboard' | 'income' | 'deductions' | 'comparison' | 'explanation' | 'history';

const TABS: { id: Tab; label: string; icon: any }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: Calculator },
  { id: 'income', label: 'Income Inputs', icon: Wallet },
  { id: 'deductions', label: 'Deductions', icon: ReceiptText },
  { id: 'comparison', label: 'Old vs New', icon: TrendingDown },
  { id: 'explanation', label: 'Explanation', icon: Info },
  { id: 'history', label: 'History & Profiles', icon: History },
];

const COLORS = ['#0f766e', '#14b8a6', '#f59e0b', '#6366f1', '#ef4444', '#64748b'];

function num(v: any): number { const n = Number(v); return Number.isFinite(n) ? n : 0; }
function cls(...a: (string|false|undefined|null)[]) { return a.filter(Boolean).join(' '); }

function Card({ children, className='' }: { children: any; className?: string }) {
  return <div className={cls('bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-soft', className)}>{children}</div>;
}
function CardHeader({ title, subtitle, right }: { title: string; subtitle?: string; right?: any }) {
  return <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-start justify-between gap-4">
    <div><h3 className="font-semibold text-slate-900 dark:text-slate-100">{title}</h3>{subtitle && <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>}</div>
    {right}
  </div>;
}
function Field({ label, children, hint }: { label: string; children: any; hint?: string }) {
  return <label className="block"><span className="text-sm font-medium text-slate-700 dark:text-slate-300">{label}</span><div className="mt-1">{children}</div>{hint && <span className="text-xs text-slate-500 mt-1 block">{hint}</span>}</label>;
}
function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cls('w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500', props.className)} />;
}
function NumInput({ value, onChange, min=0 }: { value: number; onChange: (n: number)=>void; min?: number }) {
  return <Input type="number" min={min} step="any" value={value === 0 ? 0 : value} onChange={e => onChange(Math.max(min, num(e.target.value)))} />;
}
function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cls('w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500', props.className)} />;
}
function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v:boolean)=>void; label: string }) {
  return <label className="inline-flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer">
    <input type="checkbox" checked={checked} onChange={e=>onChange(e.target.checked)} className="rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
    {label}
  </label>;
}
function StatCard({ title, value, sub, accent='brand' }: { title: string; value: string; sub?: string; accent?: string }) {
  const accentClass: any = { brand: 'text-brand-700 dark:text-brand-400', green: 'text-emerald-700 dark:text-emerald-400', amber: 'text-amber-700 dark:text-amber-400', red: 'text-rose-700 dark:text-rose-400' };
  return <Card className="p-5"><div className="text-sm text-slate-500 dark:text-slate-400">{title}</div><div className={cls('text-2xl font-semibold mt-2', accentClass[accent] || accentClass.brand)}>{value}</div>{sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}</Card>;
}

export default function App() {
  const [dark, setDark] = useState(() => localStorage.getItem('theme') === 'dark');
  const [tab, setTab] = useState<Tab>('dashboard');
  const [req, setReq] = useState<TaxCalculationRequest>(defaultRequest());
  const [result, setResult] = useState<TaxResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [profiles, setProfiles] = useState<ProfileRecord[]>([]);
  const [years, setYears] = useState<any[]>([]);
  const [profileName, setProfileName] = useState('');

  useEffect(() => { document.documentElement.classList.toggle('dark', dark); localStorage.setItem('theme', dark ? 'dark' : 'light'); }, [dark]);
  useEffect(() => { api.years().then(r => setYears(r.financial_years || [])).catch(()=>{}); refreshHistory(); refreshProfiles(); }, []);

  async function refreshHistory() { try { const r = await api.history(); setHistory(r.items || []); } catch {} }
  async function refreshProfiles() { try { const r = await api.profiles(); setProfiles(r.items || []); } catch {} }

  function update(path: string, value: any) {
    setReq(prev => {
      const next: any = structuredClone(prev);
      const parts = path.split('.');
      let cur = next;
      for (let i=0; i<parts.length-1; i++) cur = cur[parts[i]];
      cur[parts[parts.length-1]] = value;
      return next;
    });
  }

  async function calculate(regime: 'old'|'new'|'compare' = 'compare', save=false) {
    setLoading(true); setError(null);
    try {
      const payload: TaxCalculationRequest = { ...req, regime, save_history: save, profile_name: profileName || req.profile_name || null };
      const r = regime === 'compare' ? await api.compare(payload) : await api.calculate(payload);
      setResult(r);
      if (save) await refreshHistory();
      if (regime === 'compare') setTab('dashboard');
    } catch (e: any) { setError(e.message || 'Calculation failed'); }
    finally { setLoading(false); }
  }

  async function exportPdf() {
    try {
      const blob = await api.exportPdf({ ...req, regime: req.regime || 'compare' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `tax-report-${req.profile.financial_year}.pdf`; a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) { setError(e.message || 'Export failed'); }
  }

  function resetAll() { setReq(defaultRequest()); setResult(null); setError(null); setProfileName(''); }

  async function saveProfile() {
    if (!profileName.trim()) { setError('Enter a profile name before saving.'); return; }
    try {
      await api.createProfile({ name: profileName.trim(), age_category: req.profile.age_category, resident: req.profile.resident, taxpayer_type: req.profile.taxpayer_type });
      await refreshProfiles();
    } catch (e: any) { setError(e.message); }
  }

  async function loadHistoryItem(id: string) {
    try {
      const item = await api.historyItem(id);
      if (item.input) { setReq(item.input); setResult(item.result); setTab('dashboard'); }
    } catch (e: any) { setError(e.message); }
  }

  const summary = useMemo(() => {
    const r: any = result;
    if (!r) return null;
    const isCompare = !!r.comparison_table;
    const oldR = isCompare ? r.old_regime : (r.regime === 'old' ? r : null);
    const newR = isCompare ? r.new_regime : (r.regime === 'new' ? r : null);
    const active = newR || oldR || r;
    const gross = num(active?.income?.gross_total_income);
    const deductions = num(active?.deductions?.total_allowed);
    const taxable = num(active?.tax_computation?.total_taxable_income);
    const finalTax = num(active?.tax_computation?.final_tax_liability);
    const effective = num(active?.tax_computation?.effective_tax_rate_percent);
    return { isCompare, oldR, newR, active, gross, deductions, taxable, finalTax, effective, recommended: r.recommended_regime, savings: num(r.savings) };
  }, [result]);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 backdrop-blur bg-white/85 dark:bg-slate-950/85 border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-700 text-white flex items-center justify-center"><IndianRupee size={20} /></div>
            <div>
              <div className="font-semibold text-slate-900 dark:text-white leading-tight">Indian Income Tax Calculator</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">FY 2026-27 / AY 2027-28 • Offline • Privacy-first</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setDark(d => !d)} className="p-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800" title="Toggle theme">{dark ? <Sun size={16}/> : <Moon size={16}/>}</button>
            <button onClick={exportPdf} className="hidden sm:inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"><FileDown size={16}/> Export PDF</button>
            <button onClick={() => calculate('compare', false)} disabled={loading} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-700 hover:bg-brand-800 text-white text-sm font-medium disabled:opacity-60"><Calculator size={16}/>{loading ? 'Calculating...' : 'Calculate & Compare'}</button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {error && <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900/50 dark:bg-rose-950/30 dark:text-rose-300 px-4 py-3 text-sm flex justify-between gap-4"><span>{error}</span><button onClick={()=>setError(null)} className="text-rose-500">Dismiss</button></div>}

        <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-6">
          <aside className="lg:sticky lg:top-24 self-start">
            <Card className="p-2">
              {TABS.map(t => { const Icon=t.icon; const active=tab===t.id; return (
                <button key={t.id} onClick={()=>setTab(t.id)} className={cls('w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-left transition', active ? 'bg-brand-50 text-brand-800 dark:bg-brand-950/40 dark:text-brand-300 font-medium' : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60')}>
                  <Icon size={16} /> {t.label}
                </button>
              );})}
            </Card>
            <Card className="p-4 mt-4 space-y-3">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Taxpayer</div>
              <Field label="Financial Year">
                <Select value={req.profile.financial_year} onChange={e=>update('profile.financial_year', e.target.value)}>
                  {(years.length ? years : [{financial_year:'2026-27', label:'FY 2026-27 (AY 2027-28)'}]).map((y:any)=><option key={y.financial_year} value={y.financial_year}>{y.label || y.financial_year}</option>)}
                </Select>
              </Field>
              <Field label="Age Category">
                <Select value={req.profile.age_category} onChange={e=>update('profile.age_category', e.target.value)}>
                  <option value="below_60">Below 60</option>
                  <option value="senior_60_to_79">Senior (60-79)</option>
                  <option value="super_senior_80_plus">Super Senior (80+)</option>
                </Select>
              </Field>
              <Toggle checked={req.profile.resident} onChange={v=>update('profile.resident', v)} label="Resident individual" />
              <Field label="Profile name (optional)">
                <Input value={profileName} onChange={e=>setProfileName(e.target.value)} placeholder="e.g. Self, Spouse" />
              </Field>
              <div className="flex gap-2">
                <button onClick={saveProfile} className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800">Save Profile</button>
                <button onClick={resetAll} className="px-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800" title="Reset"><RotateCcw size={15}/></button>
              </div>
            </Card>
          </aside>

          <main className="space-y-6">
            {tab === 'dashboard' && <Dashboard summary={summary} result={result} onCalculate={calculate} loading={loading} />}
            {tab === 'income' && <IncomeForm req={req} update={update} />}
            {tab === 'deductions' && <DeductionsForm req={req} update={update} />}
            {tab === 'comparison' && <ComparisonView result={result} />}
            {tab === 'explanation' && <ExplanationView result={result} />}
            {tab === 'history' && <HistoryView history={history} profiles={profiles} onLoad={loadHistoryItem} onDelete={async (id: string)=>{await api.deleteHistory(id); refreshHistory();}} onDeleteProfile={async(id: string)=>{await api.deleteProfile(id); refreshProfiles();}} onUseProfile={(p: ProfileRecord)=>{setProfileName(p.name); update('profile.age_category', p.age_category); update('profile.resident', p.resident); update('profile.taxpayer_type', p.taxpayer_type);}} />}

            <div className="flex flex-wrap gap-3">
              <button onClick={()=>calculate('compare', false)} disabled={loading} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand-700 hover:bg-brand-800 text-white text-sm font-medium disabled:opacity-60"><Calculator size={16}/> Calculate & Compare</button>
              <button onClick={()=>calculate('compare', true)} disabled={loading} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-sm hover:bg-slate-50 dark:hover:bg-slate-800"><Save size={16}/> Save Calculation</button>
              <button onClick={exportPdf} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-sm hover:bg-slate-50 dark:hover:bg-slate-800"><FileDown size={16}/> Export PDF</button>
              <button onClick={resetAll} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 text-sm hover:bg-slate-50 dark:hover:bg-slate-800"><RotateCcw size={16}/> Reset</button>
            </div>

            <div className="text-xs text-slate-500 dark:text-slate-400 p-4 border border-slate-200 dark:border-slate-800 rounded-xl bg-slate-50 dark:bg-slate-900/40">
              <strong>Disclaimer:</strong> This calculator provides estimates based on configured FY 2026-27 rules and the inputs you provide. It is not professional tax advice. Tax laws are complex and subject to change/interpretation. Verify with official Income Tax Department resources or a qualified tax professional before filing.
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

function Dashboard({ summary, result, onCalculate, loading }: any) {
  const r: any = result;
  const s = summary;
  const compare = r?.comparison_table ? r : null;
  const oldR = compare?.old_regime || (r?.regime === 'old' ? r : null);
  const newR = compare?.new_regime || (r?.regime === 'new' ? r : null);
  const active = newR || oldR || r;

  const incomeData = useMemo(() => {
    if (!active?.income) return [];
    const i = active.income;
    return [
      { name: 'Salary', value: num(i.salary?.net_salary_income) },
      { name: 'House Property', value: Math.max(0, num(i.house_property?.income_or_loss_for_setoff ?? i.house_property?.income_or_loss)) },
      { name: 'Capital Gains', value: num(i.capital_gains?.slab_rate_capital_gains_income) + num(i.capital_gains?.special_rate_tax ? 0 : 0) + num(i.capital_gains?.ltcg_112a_total) },
      { name: 'Business/Prof.', value: num(i.business_professional?.total) },
      { name: 'Other Sources', value: num(i.other_sources?.total) },
    ].filter(d => d.value > 0);
  }, [active]);

  const taxCompareData = useMemo(() => {
    if (!oldR && !newR) return [];
    return [
      { name: 'Old Regime', tax: num(oldR?.tax_computation?.final_tax_liability), deductions: num(oldR?.deductions?.total_allowed) },
      { name: 'New Regime', tax: num(newR?.tax_computation?.final_tax_liability), deductions: num(newR?.deductions?.total_allowed) },
    ].filter(d => d.tax > 0 || d.deductions > 0);
  }, [oldR, newR]);

  const deductionData = useMemo(() => {
    const items = (active?.deductions?.items || []).filter((i:any)=>num(i.allowed)>0);
    return items.map((i:any)=>({ name: i.section || i.name, value: num(i.allowed) }));
  }, [active]);

  if (!s) {
    return (
      <Card className="p-10 text-center">
        <div className="w-14 h-14 rounded-2xl bg-brand-50 dark:bg-brand-950/40 text-brand-700 dark:text-brand-400 flex items-center justify-center mx-auto"><Calculator size={28} /></div>
        <h2 className="text-xl font-semibold mt-4">Calculate your Indian income tax</h2>
        <p className="text-slate-500 dark:text-slate-400 mt-2 max-w-xl mx-auto">Enter your income and deduction details, then compare the Old and New tax regimes for FY 2026-27. All calculations run locally and your data stays on your device.</p>
        <button onClick={() => onCalculate('compare')} disabled={loading} className="mt-6 inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-brand-700 hover:bg-brand-800 text-white font-medium disabled:opacity-60"><Calculator size={16}/> Calculate with sample/entered values</button>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
        <StatCard title="Gross Total Income" value={inr(s.gross)} sub="All income heads" />
        <StatCard title="Total Deductions" value={inr(s.deductions)} sub="Allowed under selected regime" />
        <StatCard title="Taxable Income" value={inr(s.taxable)} sub="After deductions & exemptions" />
        <StatCard title="Estimated Tax" value={inr(compare ? Math.min(num(oldR?.tax_computation?.final_tax_liability), num(newR?.tax_computation?.final_tax_liability)) : s.finalTax)} sub={compare ? `Best of both regimes` : 'Final liability incl. cess'} accent="green" />
        <StatCard title="Effective Tax Rate" value={pct(s.effective)} sub="Tax / gross total income" accent="amber" />
      </div>

      {compare && (
        <Card className="p-5 border-brand-200 dark:border-brand-900/50 bg-brand-50/50 dark:bg-brand-950/10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="text-sm text-slate-500 dark:text-slate-400">Recommendation</div>
              <div className="text-lg font-semibold text-slate-900 dark:text-white mt-1">
                {s.recommended === 'either' ? 'Both regimes result in similar tax.' : `${s.recommended === 'old' ? 'Old' : 'New'} Regime saves you ${inr(s.savings)}`}
              </div>
              <div className="text-sm text-slate-600 dark:text-slate-400 mt-1">Old: {inr(oldR?.tax_computation?.final_tax_liability)} • New: {inr(newR?.tax_computation?.final_tax_liability)}</div>
            </div>
            <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white dark:bg-slate-900 border border-brand-200 dark:border-brand-900 text-brand-800 dark:text-brand-300 text-sm font-medium"><CheckCircle2 size={16}/> {s.recommended === 'either' ? 'Equal' : `${s.recommended === 'old' ? 'Old' : 'New'} Regime`}</div>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Income Distribution" subtitle="Gross income by head" />
          <div className="p-5 h-72">
            {incomeData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={incomeData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={95} paddingAngle={2}>
                    {incomeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v:any)=>inr(v)} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : <div className="h-full flex items-center justify-center text-sm text-slate-500">Enter income to see distribution.</div>}
          </div>
        </Card>
        <Card>
          <CardHeader title="Old vs New Regime" subtitle="Final tax and deductions comparison" />
          <div className="p-5 h-72">
            {taxCompareData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={taxCompareData}>
                  <XAxis dataKey="name" />
                  <YAxis tickFormatter={(v)=>`₹${Math.round(v/1000)}k`} />
                  <Tooltip formatter={(v:any)=>inr(v)} />
                  <Legend />
                  <Bar dataKey="tax" name="Final Tax" fill="#0f766e" radius={[6,6,0,0]} />
                  <Bar dataKey="deductions" name="Deductions" fill="#94a3b8" radius={[6,6,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="h-full flex items-center justify-center text-sm text-slate-500">Run a comparison to see chart.</div>}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Deduction Breakdown" subtitle="Allowed deductions used in calculation" />
          <div className="p-5 h-72">
            {deductionData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={deductionData} layout="vertical" margin={{left:20}}>
                  <XAxis type="number" tickFormatter={(v)=>`₹${Math.round(v/1000)}k`} />
                  <YAxis type="category" dataKey="name" width={90} />
                  <Tooltip formatter={(v:any)=>inr(v)} />
                  <Bar dataKey="value" name="Allowed" fill="#14b8a6" radius={[0,6,6,0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="h-full flex items-center justify-center text-sm text-slate-500">No deductions applied yet.</div>}
          </div>
        </Card>
        <Card>
          <CardHeader title="Quick Summary" subtitle="Active calculation snapshot" />
          <div className="p-5 space-y-3 text-sm">
            {[
              ['Financial Year', active?.financial_year || '2026-27'],
              ['Gross Total Income', inr(active?.income?.gross_total_income)],
              ['Total Deductions', inr(active?.deductions?.total_allowed)],
              ['Taxable Income', inr(active?.tax_computation?.total_taxable_income)],
              ['Tax Before Rebate', inr(active?.tax_computation?.tax_before_rebate)],
              ['Rebate (87A)', inr(active?.tax_computation?.rebate_87a)],
              ['Surcharge', inr(active?.tax_computation?.surcharge?.surcharge)],
              ['Cess', inr(active?.tax_computation?.cess)],
              ['Final Tax Liability', inr(active?.tax_computation?.final_tax_liability)],
            ].map(([k,v]) => (
              <div key={String(k)} className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
                <span className="text-slate-500 dark:text-slate-400">{k}</span><span className="font-medium text-slate-900 dark:text-slate-100">{v}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function SectionTitle({ icon: Icon, title, subtitle }: any) {
  return <div className="flex items-center gap-3 mb-4"><div className="w-9 h-9 rounded-lg bg-brand-50 dark:bg-brand-950/40 text-brand-700 dark:text-brand-400 flex items-center justify-center"><Icon size={18}/></div><div><div className="font-semibold">{title}</div>{subtitle && <div className="text-sm text-slate-500 dark:text-slate-400">{subtitle}</div>}</div></div>;
}

function IncomeForm({ req, update }: { req: TaxCalculationRequest; update: (p:string,v:any)=>void }) {
  const addCg = () => update('capital_gains.entries', [...req.capital_gains.entries, { asset_type: 'equity_ltcg_112a', gain_amount: 0, acquired_before_2024_07_23: false, indexed_cost_available: false, indexed_gain_amount: null } as CapitalGainEntry]);
  const removeCg = (i: number) => update('capital_gains.entries', req.capital_gains.entries.filter((_, idx) => idx !== i));
  const setCg = (i: number, k: string, v: any) => { const next = req.capital_gains.entries.map((e, idx) => idx===i ? { ...e, [k]: v } : e); update('capital_gains.entries', next); };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title="Salary Income" subtitle="Enter annual amounts in INR" />
        <div className="p-5 space-y-5">
          <SectionTitle icon={Briefcase} title="Salary components" subtitle="Standard deduction is applied automatically based on selected regime." />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            <Field label="Basic Salary"><NumInput value={req.salary.basic_salary} onChange={v=>update('salary.basic_salary',v)} /></Field>
            <Field label="HRA Received"><NumInput value={req.salary.hra_received} onChange={v=>update('salary.hra_received',v)} /></Field>
            <Field label="Special Allowance"><NumInput value={req.salary.special_allowance} onChange={v=>update('salary.special_allowance',v)} /></Field>
            <Field label="Other Allowances"><NumInput value={req.salary.other_allowances} onChange={v=>update('salary.other_allowances',v)} /></Field>
            <Field label="Bonus"><NumInput value={req.salary.bonus} onChange={v=>update('salary.bonus',v)} /></Field>
            <Field label="Other Taxable Components"><NumInput value={req.salary.other_taxable_components} onChange={v=>update('salary.other_taxable_components',v)} /></Field>
            <Field label="Professional Tax Paid" hint="Deductible in old regime only."><NumInput value={req.salary.professional_tax_paid} onChange={v=>update('salary.professional_tax_paid',v)} /></Field>
            <Field label="Employer NPS Contribution (80CCD(2))" hint="Deductible in both regimes, subject to cap."><NumInput value={req.salary.employer_nps_contribution} onChange={v=>update('salary.employer_nps_contribution',v)} /></Field>
            <Field label="Rent Paid Per Year" hint="Used for HRA exemption in old regime."><NumInput value={req.salary.rent_paid_per_year} onChange={v=>update('salary.rent_paid_per_year',v)} /></Field>
          </div>
          <Toggle checked={req.salary.is_metro} onChange={v=>update('salary.is_metro',v)} label="Metro city for HRA (Delhi/Mumbai/Kolkata/Chennai = 50%)" />
        </div>
      </Card>

      <Card>
        <CardHeader title="House Property Income" subtitle="Self-occupied or let-out property" />
        <div className="p-5 space-y-4">
          <SectionTitle icon={Building2} title="Property details" subtitle="Old regime allows self-occupied interest deduction (cap ₹2L). New regime has restrictions." />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            <Field label="Property Type">
              <Select value={req.house_property.property_type} onChange={e=>update('house_property.property_type', e.target.value)}>
                <option value="self_occupied">Self Occupied</option>
                <option value="let_out">Let Out</option>
              </Select>
            </Field>
            <Field label="Annual Rent Received"><NumInput value={req.house_property.annual_rent_received} onChange={v=>update('house_property.annual_rent_received',v)} /></Field>
            <Field label="Municipal Taxes Paid"><NumInput value={req.house_property.municipal_taxes_paid} onChange={v=>update('house_property.municipal_taxes_paid',v)} /></Field>
            <Field label="Home Loan Interest"><NumInput value={req.house_property.home_loan_interest} onChange={v=>update('house_property.home_loan_interest',v)} /></Field>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader title="Capital Gains" subtitle="Add gains by asset type" right={<button onClick={addCg} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm bg-brand-700 text-white hover:bg-brand-800"><Plus size={15}/> Add Gain</button>} />
        <div className="p-5 space-y-4">
          <SectionTitle icon={LineChart} title="Capital gain entries" subtitle="Special rates applied where applicable (111A/112A/112)." />
          {req.capital_gains.entries.length === 0 && <div className="text-sm text-slate-500">No capital gains added.</div>}
          {req.capital_gains.entries.map((e, i) => (
            <div key={i} className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
              <Field label="Asset Type">
                <Select value={e.asset_type} onChange={ev=>setCg(i,'asset_type',ev.target.value)}>
                  <option value="equity_stcg_111a">Equity STCG (111A, 20%)</option>
                  <option value="equity_ltcg_112a">Equity LTCG (112A, 12.5%)</option>
                  <option value="debt_mf_post_2023_04_01">Debt MF post 1-Apr-2023 (slab)</option>
                  <option value="property_ltcg">Property LTCG (12.5%)</option>
                  <option value="other_ltcg">Other LTCG (12.5%)</option>
                  <option value="other_stcg">Other STCG (slab)</option>
                </Select>
              </Field>
              <Field label="Gain Amount"><NumInput value={e.gain_amount} onChange={v=>setCg(i,'gain_amount',v)} /></Field>
              <Field label="Indexed Gain (property grandfathering)">
                <NumInput value={num(e.indexed_gain_amount)} onChange={v=>setCg(i,'indexed_gain_amount',v)} />
              </Field>
              <div className="flex items-end pb-2"><Toggle checked={!!e.acquired_before_2024_07_23} onChange={v=>setCg(i,'acquired_before_2024_07_23',v)} label="Acquired before 23-Jul-2024" /></div>
              <div className="flex items-end justify-end pb-1"><button onClick={()=>removeCg(i)} className="p-2 rounded-lg text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"><Trash2 size={16}/></button></div>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card>
          <CardHeader title="Business & Professional Income" subtitle="Profits or presumptive income" />
          <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Profits from Business"><NumInput value={req.business.profits_from_business} onChange={v=>update('business.profits_from_business',v)} /></Field>
            <Field label="Professional Income"><NumInput value={req.business.professional_income} onChange={v=>update('business.professional_income',v)} /></Field>
            <Field label="Presumptive Income"><NumInput value={req.business.presumptive_income} onChange={v=>update('business.presumptive_income',v)} /></Field>
            <Field label="Presumptive Scheme">
              <Select value={req.business.presumptive_scheme} onChange={e=>update('business.presumptive_scheme',e.target.value)}>
                <option value="none">None / Not applicable</option>
                <option value="44ad">44AD</option>
                <option value="44ada">44ADA</option>
                <option value="44ae">44AE</option>
              </Select>
            </Field>
          </div>
        </Card>
        <Card>
          <CardHeader title="Other Income" subtitle="Interest, dividends, and other sources" />
          <div className="p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Savings Account Interest"><NumInput value={req.other_income.savings_account_interest} onChange={v=>update('other_income.savings_account_interest',v)} /></Field>
            <Field label="Fixed Deposit Interest"><NumInput value={req.other_income.fixed_deposit_interest} onChange={v=>update('other_income.fixed_deposit_interest',v)} /></Field>
            <Field label="Dividend Income"><NumInput value={req.other_income.dividend_income} onChange={v=>update('other_income.dividend_income',v)} /></Field>
            <Field label="Family Pension"><NumInput value={req.other_income.family_pension} onChange={v=>update('other_income.family_pension',v)} /></Field>
            <Field label="Other Taxable Income"><NumInput value={req.other_income.other_taxable_income} onChange={v=>update('other_income.other_taxable_income',v)} /></Field>
          </div>
        </Card>
      </div>
    </div>
  );
}

function DeductionsForm({ req, update }: { req: TaxCalculationRequest; update: (p:string,v:any)=>void }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title="Deductions & Exemptions" subtitle="Eligibility depends on the selected tax regime" />
        <div className="p-5 space-y-5">
          <div className="text-sm text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/40 rounded-lg p-3">
            New regime allows limited deductions (standard deduction, employer NPS 80CCD(2), etc.). Old regime allows most Chapter VI-A deductions. The calculator applies regime eligibility automatically.
          </div>
          <SectionTitle icon={ReceiptText} title="Chapter VI-A deductions" subtitle="Enter annual amounts. Caps and eligibility are enforced by the engine." />
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            <Field label="Section 80C" hint="Old regime only. Cap ₹1,50,000."><NumInput value={req.deductions.section_80c} onChange={v=>update('deductions.section_80c',v)} /></Field>
            <Field label="Section 80CCD(1B) - NPS" hint="Old regime only. Additional ₹50,000."><NumInput value={req.deductions.section_80ccd_1b} onChange={v=>update('deductions.section_80ccd_1b',v)} /></Field>
            <Field label="Section 80G - Eligible Donation" hint="Old regime only. Simplified input; verify category limits."><NumInput value={req.deductions.section_80g_eligible_donation} onChange={v=>update('deductions.section_80g_eligible_donation',v)} /></Field>
            <Field label="Section 80TTA - Savings Interest" hint="Old regime, non-senior. Cap ₹10,000."><NumInput value={req.deductions.section_80tta} onChange={v=>update('deductions.section_80tta',v)} /></Field>
            <Field label="Section 80TTB - Interest (Senior)" hint="Old regime, senior citizens. Cap ₹50,000."><NumInput value={req.deductions.section_80ttb} onChange={v=>update('deductions.section_80ttb',v)} /></Field>
          </div>

          <div className="border-t border-slate-100 dark:border-slate-800 pt-5">
            <div className="font-medium mb-3">Section 80D - Medical Insurance</div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              <Field label="Self/Family Premium"><NumInput value={req.deductions.section_80d_self_family} onChange={v=>update('deductions.section_80d_self_family',v)} /></Field>
              <div className="flex items-end pb-2"><Toggle checked={req.deductions.section_80d_self_family_is_senior} onChange={v=>update('deductions.section_80d_self_family_is_senior',v)} label="Self/family senior citizen" /></div>
              <Field label="Parents Premium"><NumInput value={req.deductions.section_80d_parents} onChange={v=>update('deductions.section_80d_parents',v)} /></Field>
              <div className="flex items-end pb-2"><Toggle checked={req.deductions.section_80d_parents_is_senior} onChange={v=>update('deductions.section_80d_parents_is_senior',v)} label="Parents are senior citizens" /></div>
              <Field label="Preventive Health Checkup" hint="Within overall 80D limits."><NumInput value={req.deductions.section_80d_preventive_checkup} onChange={v=>update('deductions.section_80d_preventive_checkup',v)} /></Field>
            </div>
          </div>

          <div className="border-t border-slate-100 dark:border-slate-800 pt-5">
            <div className="font-medium mb-2">Other notes</div>
            <p className="text-sm text-slate-500 dark:text-slate-400">HRA exemption is captured in the Salary section (old regime). Home loan interest is captured in House Property. Employer NPS (80CCD(2)) is captured in Salary and is allowed in both regimes subject to limits.</p>
          </div>
        </div>
      </Card>
    </div>
  );
}

function ComparisonView({ result }: { result: TaxResult | null }) {
  const r: any = result;
  const table = r?.comparison_table;
  if (!table) {
    return <Card className="p-10 text-center text-slate-500"><div className="font-medium text-slate-700 dark:text-slate-200">No comparison yet</div><div className="mt-1 text-sm">Run "Calculate & Compare" to see old vs new regime side by side.</div></Card>;
  }
  const recommended = r.recommended_regime;
  const savings = num(r.savings);
  return (
    <div className="space-y-6">
      <Card className="p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Old vs New Tax Regime</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{recommended === 'either' ? 'Both regimes result in the same tax.' : `${recommended === 'old' ? 'Old' : 'New'} regime is better by ${inr(savings)}.`}</p>
          </div>
          <div className={cls('px-3 py-2 rounded-lg text-sm font-medium', recommended === 'new' ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300' : recommended === 'old' ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300' : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300')}>
            {recommended === 'either' ? 'Equal' : `${recommended.toUpperCase()} regime recommended`}
          </div>
        </div>
      </Card>
      <Card>
        <CardHeader title="Detailed Comparison" subtitle="All amounts in INR" />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/60 text-slate-600 dark:text-slate-300">
                <th className="text-left px-5 py-3 font-medium">Particulars</th>
                <th className="text-right px-5 py-3 font-medium">Old Regime</th>
                <th className="text-right px-5 py-3 font-medium">New Regime</th>
                <th className="text-right px-5 py-3 font-medium">Difference</th>
              </tr>
            </thead>
            <tbody>
              {table.map((row: any, i: number) => {
                const oldV = num(row.old_regime); const newV = num(row.new_regime); const diff = oldV - newV;
                const highlight = row.particular === 'Final Tax Liability';
                return (
                  <tr key={i} className={cls('border-t border-slate-100 dark:border-slate-800', highlight && 'bg-brand-50/40 dark:bg-brand-950/10 font-semibold')}>
                    <td className="px-5 py-3">{row.particular}</td>
                    <td className="px-5 py-3 text-right">{inr(oldV)}</td>
                    <td className="px-5 py-3 text-right">{inr(newV)}</td>
                    <td className={cls('px-5 py-3 text-right', diff > 0 ? 'text-emerald-600' : diff < 0 ? 'text-rose-600' : 'text-slate-500')}>{diff === 0 ? '—' : `${diff > 0 ? 'Old +' : 'New +'}${inr(Math.abs(diff))}`}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function ExplanationView({ result }: { result: TaxResult | null }) {
  const r: any = result;
  if (!r) return <Card className="p-10 text-center text-slate-500"><div className="font-medium text-slate-700 dark:text-slate-200">No calculation yet</div><div className="mt-1 text-sm">Calculate tax to see a step-by-step explanation.</div></Card>;
  const regimes = r.comparison_table ? [{label:'Old Regime', data:r.old_regime}, {label:'New Regime', data:r.new_regime}] : [{label: r.regime === 'old' ? 'Old Regime' : 'New Regime', data:r}];
  return (
    <div className="space-y-6">
      {regimes.map((reg:any) => (
        <Card key={reg.label}>
          <CardHeader title={`${reg.label} — Step-by-step explanation`} subtitle="How your tax was calculated" />
          <div className="p-5 space-y-4">
            {(reg.data?.explanation || []).map((step:any) => (
              <div key={step.step} className="rounded-xl border border-slate-200 dark:border-slate-800 p-4">
                <div className="flex items-center gap-2 font-medium"><span className="w-6 h-6 rounded-full bg-brand-100 dark:bg-brand-950/50 text-brand-700 dark:text-brand-300 text-xs flex items-center justify-center">{step.step}</span>{step.title}</div>
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                  {Object.entries(step.details || {}).map(([k,v]) => (
                    <div key={k} className="flex justify-between gap-4 py-1 border-b border-slate-100 dark:border-slate-800 last:border-0">
                      <span className="text-slate-500 dark:text-slate-400">{k.replace(/_/g,' ')}</span>
                      <span className="font-medium text-right">{typeof v === 'number' ? inr(v) : Array.isArray(v) ? v.join('; ') : String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            {(reg.data?.assumptions_and_notes || []).filter(Boolean).length > 0 && (
              <div className="rounded-xl bg-slate-50 dark:bg-slate-800/40 p-4 text-sm">
                <div className="font-medium mb-2">Assumptions & notes</div>
                <ul className="list-disc pl-5 space-y-1 text-slate-600 dark:text-slate-400">
                  {reg.data.assumptions_and_notes.filter(Boolean).map((n:string,i:number)=><li key={i}>{n}</li>)}
                </ul>
              </div>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
}

function HistoryView({ history, profiles, onLoad, onDelete, onDeleteProfile, onUseProfile }: any) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader title="Saved Profiles" subtitle="Reuse taxpayer details for quick calculations" />
        <div className="p-5">
          {profiles.length === 0 ? <div className="text-sm text-slate-500">No profiles saved yet.</div> : (
            <div className="space-y-2">
              {profiles.map((p: ProfileRecord) => (
                <div key={p.id} className="flex items-center justify-between gap-4 p-3 rounded-lg border border-slate-200 dark:border-slate-800">
                  <div>
                    <div className="font-medium">{p.name}</div>
                    <div className="text-xs text-slate-500">{p.age_category.replace(/_/g,' ')} • {p.resident ? 'Resident' : 'Non-resident'} • {p.taxpayer_type}</div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={()=>onUseProfile(p)} className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800">Use</button>
                    <button onClick={()=>onDeleteProfile(p.id)} className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"><Trash2 size={15}/></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader title="Calculation History" subtitle="Previously saved calculations" />
        <div className="p-5">
          {history.length === 0 ? <div className="text-sm text-slate-500">No saved calculations yet. Use "Save Calculation" after calculating.</div> : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-slate-500 border-b border-slate-200 dark:border-slate-800">
                  <th className="py-2 pr-3">Date</th><th className="py-2 pr-3">Profile</th><th className="py-2 pr-3">FY</th><th className="py-2 pr-3">Regime</th><th className="py-2 pr-3 text-right">Gross</th><th className="py-2 pr-3 text-right">Old Tax</th><th className="py-2 pr-3 text-right">New Tax</th><th className="py-2">Actions</th>
                </tr></thead>
                <tbody>
                  {history.map((h: HistoryItem) => (
                    <tr key={h.id} className="border-b border-slate-100 dark:border-slate-800 last:border-0">
                      <td className="py-2 pr-3 whitespace-nowrap">{new Date(h.created_at).toLocaleString()}</td>
                      <td className="py-2 pr-3">{h.profile_name || '—'}</td>
                      <td className="py-2 pr-3">{h.financial_year}</td>
                      <td className="py-2 pr-3">{h.recommended_regime ? `Compare (${h.recommended_regime})` : h.regime}</td>
                      <td className="py-2 pr-3 text-right">{inr(h.gross_total_income)}</td>
                      <td className="py-2 pr-3 text-right">{h.total_tax_old ? inr(h.total_tax_old) : '—'}</td>
                      <td className="py-2 pr-3 text-right">{h.total_tax_new ? inr(h.total_tax_new) : '—'}</td>
                      <td className="py-2">
                        <div className="flex gap-2">
                          <button onClick={()=>onLoad(h.id)} className="px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800">Load</button>
                          <button onClick={()=>onDelete(h.id)} className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30"><Trash2 size={15}/></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
