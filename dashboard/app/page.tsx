"use client";
import { useEffect, useState } from "react";

type Analytics = {
  total_beneficiaries: number;
  total_queries: number;
  top_schemes: { scheme_id: string; count: number }[];
  language_distribution: Record<string, number>;
  recent_queries: { query: string; language: string; schemes_matched: number; created_at: string }[];
};

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Page() {
  const [data, setData] = useState<Analytics | null>(null);
  const [demoQuery, setDemoQuery] = useState("Main ek 30 saal ki mahila hu, gaon mein rehti hu, 2 bache hai");
  const [demoOut, setDemoOut] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    try {
      const r = await fetch(`${API}/api/analytics`, { cache: "no-store" });
      setData(await r.json());
    } catch {}
  }
  useEffect(() => {
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  async function runDemo() {
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("query", demoQuery);
      const r = await fetch(`${API}/api/demo`, { method: "POST", body: fd });
      setDemoOut(await r.json());
    } catch (e: any) {
      setDemoOut({ error: String(e) });
    }
    setLoading(false);
  }

  const maxTop = Math.max(1, ...(data?.top_schemes.map((s) => s.count) || [1]));
  const langs = data ? Object.entries(data.language_distribution) : [];
  const langTotal = langs.reduce((a, [, v]) => a + v, 0) || 1;

  return (
    <main className="max-w-6xl mx-auto p-6 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">SchemeSaathi Impact Dashboard</h1>
          <p className="text-slate-400">WhatsApp voice → eligible govt schemes • auto-refresh 30s</p>
        </div>
        <button onClick={load} className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500">Refresh</button>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card"><p className="text-slate-400 text-sm">Beneficiaries helped</p><p className="text-4xl font-bold">{data?.total_beneficiaries ?? "—"}</p></div>
        <div className="card"><p className="text-slate-400 text-sm">Queries processed</p><p className="text-4xl font-bold">{data?.total_queries ?? "—"}</p></div>
        <div className="card"><p className="text-slate-400 text-sm">Languages</p><p className="text-4xl font-bold">{langs.length || "—"}</p></div>
        <div className="card"><p className="text-slate-400 text-sm">Backend</p><p className="text-sm font-mono break-all">{API}</p></div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="card">
          <h2 className="font-semibold mb-3">Top 5 schemes recommended</h2>
          {(data?.top_schemes || []).map((s) => (
            <div key={s.scheme_id} className="mb-2">
              <div className="flex justify-between text-sm"><span>{s.scheme_id}</span><span>{s.count}</span></div>
              <div className="h-2 bg-slate-800 rounded"><div className="h-2 bg-emerald-500 rounded" style={{ width: `${(s.count / maxTop) * 100}%` }} /></div>
            </div>
          )) || <p className="text-slate-500 text-sm">No data yet — run a demo query below.</p>}
        </div>
        <div className="card">
          <h2 className="font-semibold mb-3">Language distribution</h2>
          {langs.map(([l, c]) => (
            <div key={l} className="mb-2">
              <div className="flex justify-between text-sm"><span>{l}</span><span>{Math.round((c / langTotal) * 100)}%</span></div>
              <div className="h-2 bg-slate-800 rounded"><div className="h-2 bg-sky-500 rounded" style={{ width: `${(c / langTotal) * 100}%` }} /></div>
            </div>
          )) || <p className="text-slate-500 text-sm">No data yet.</p>}
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold mb-3">Try demo (no WhatsApp needed)</h2>
        <div className="flex gap-2">
          <input value={demoQuery} onChange={(e) => setDemoQuery(e.target.value)} className="flex-1 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700" />
          <button onClick={runDemo} disabled={loading} className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50">{loading ? "…" : "Ask"}</button>
        </div>
        {demoOut && (
          <pre className="mt-3 text-xs bg-slate-950 border border-slate-800 rounded-xl p-3 overflow-auto max-h-96">{JSON.stringify(demoOut, null, 2).slice(0, 6000)}</pre>
        )}
      </div>

      <div className="card">
        <h2 className="font-semibold mb-3">Recent queries (anonymized)</h2>
        <table className="w-full text-sm">
          <thead><tr className="text-slate-400 text-left"><th>Query</th><th>Lang</th><th>Matched</th><th>Time</th></tr></thead>
          <tbody>
            {(data?.recent_queries || []).map((q, i) => (
              <tr key={i} className="border-t border-slate-800"><td className="py-1 pr-2">{q.query}</td><td>{q.language}</td><td>{q.schemes_matched}</td><td className="text-slate-500">{q.created_at?.slice(0, 19).replace("T", " ")}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
