import { useState, useEffect, useCallback, useRef } from "react";

const API = "/api/v1";

// ─── Theme ────────────────────────────────────────────────
const T = {
  bg: "#0c0f1a",
  surface: "#141824",
  card: "#1c2235",
  border: "#2a3555",
  gold: "#c9a84c",
  goldDim: "#8b7333",
  text: "#e8dcc8",
  dim: "#6b7a99",
  green: "#4ade80",
  red: "#f87171",
  blue: "#60a5fa",
  purple: "#a78bfa",
};

// ─── Icons (inline SVG) ──────────────────────────────────
const Icon = ({ d, size = 20, color = T.dim }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);

const Icons = {
  cross: "M12 2v20M2 12h20M7 7l10 10M17 7L7 17",
  upload: "M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12",
  search: "M11 19a8 8 0 100-16 8 8 0 000 16zM21 21l-4.35-4.35",
  plus: "M12 5v14M5 12h14",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  heart: "M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z",
  calendar: "M19 4H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V6a2 2 0 00-2-2zM16 2v4M8 2v4M3 10h18",
  check: "M20 6L9 17l-5-5",
  x: "M18 6L6 18M6 6l12 12",
  bar: "M18 20V10M12 20V4M6 20v-6",
};

// ─── Fetch helper ─────────────────────────────────────────
async function api(path, opts = {}) {
  try {
    const res = await fetch(`${API}${path}`, {
      headers: { "Content-Type": "application/json", ...opts.headers },
      ...opts,
    });
    if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`);
    return await res.json();
  } catch (e) {
    console.error("API error:", e);
    return null;
  }
}

// ─── Components ───────────────────────────────────────────

function Badge({ children, color = T.gold }) {
  return (
    <span style={{
      display: "inline-block", background: color + "22", color,
      border: `1px solid ${color}44`, borderRadius: 6,
      padding: "2px 8px", fontSize: 11, fontWeight: 600,
      fontFamily: "'JetBrains Mono', monospace",
    }}>{children}</span>
  );
}

function Tab({ active, label, icon, onClick }) {
  return (
    <button onClick={onClick} style={{
      flex: 1, display: "flex", flexDirection: "column", alignItems: "center",
      gap: 2, padding: "8px 0", background: "transparent", border: "none",
      color: active ? T.gold : T.dim, cursor: "pointer",
      borderTop: active ? `2px solid ${T.gold}` : "2px solid transparent",
      transition: "all 0.2s",
    }}>
      <Icon d={icon} size={18} color={active ? T.gold : T.dim} />
      <span style={{ fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}>{label}</span>
    </button>
  );
}

function NameCard({ name, prefix, orderType, periodType, expiresAt }) {
  const isHealth = orderType === "здравие";
  const color = isHealth ? T.green : T.red;
  const exp = expiresAt ? new Date(expiresAt) : null;
  const daysLeft = exp ? Math.max(0, Math.ceil((exp - new Date()) / 86400000)) : 0;

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "10px 14px", background: T.card, borderRadius: 8,
      borderLeft: `3px solid ${color}`, marginBottom: 6,
    }}>
      <div>
        <div style={{ color: T.text, fontSize: 15, fontWeight: 600, fontFamily: "'Cormorant Garamond', serif" }}>
          {prefix && <span style={{ color: T.dim, fontSize: 12, fontStyle: "italic", marginRight: 6 }}>{prefix}</span>}
          {name}
        </div>
        {periodType && (
          <div style={{ color: T.dim, fontSize: 11, marginTop: 2, fontFamily: "'JetBrains Mono', monospace" }}>
            {periodType} · {daysLeft} дн.
          </div>
        )}
      </div>
      <Badge color={color}>{isHealth ? "здр." : "уп."}</Badge>
    </div>
  );
}

// ─── Pages ────────────────────────────────────────────────

function TodayPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    setLoading(true);
    api("/names/today").then(d => { setData(d); setLoading(false); });
  }, []);

  if (loading) return <Loading />;
  if (!data) return <Empty msg="Не удалось загрузить данные" />;

  const groups = data.groups || {};
  const healthNames = groups["здравие"] || [];
  const restNames = groups["упокоение"] || [];

  const shown = filter === "all"
    ? [...healthNames, ...restNames]
    : filter === "здравие" ? healthNames : restNames;

  return (
    <div>
      <div style={{ padding: "16px 16px 8px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h2 style={{ margin: 0, color: T.gold, fontSize: 20, fontFamily: "'Cormorant Garamond', serif" }}>
            Имена на сегодня
          </h2>
          <div style={{ color: T.dim, fontSize: 12, fontFamily: "'JetBrains Mono', monospace", marginTop: 2 }}>
            {data.date} · {data.total} имён
          </div>
        </div>
      </div>

      {/* Filter tabs */}
      <div style={{ display: "flex", gap: 6, padding: "8px 16px" }}>
        {[
          { key: "all", label: `Все (${data.total})` },
          { key: "здравие", label: `Здравие (${healthNames.length})`, color: T.green },
          { key: "упокоение", label: `Упокоение (${restNames.length})`, color: T.red },
        ].map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)} style={{
            padding: "6px 12px", borderRadius: 6, border: "none", cursor: "pointer",
            fontSize: 11, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace",
            background: filter === f.key ? (f.color || T.gold) + "33" : T.card,
            color: filter === f.key ? (f.color || T.gold) : T.dim,
          }}>{f.label}</button>
        ))}
      </div>

      {/* Names list */}
      <div style={{ padding: "8px 16px" }}>
        {shown.length === 0 ? (
          <Empty msg="Нет активных записок на сегодня" />
        ) : (
          shown.map((n, i) => (
            <NameCard
              key={`${n.person_id}-${n.order_id}-${i}`}
              name={n.canonical_name}
              prefix={n.prefix}
              orderType={n.order_type}
              periodType={n.period_type}
              expiresAt={n.expires_at}
            />
          ))
        )}
      </div>
    </div>
  );
}

function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const timerRef = useRef(null);

  const doSearch = useCallback(async (q) => {
    if (!q || q.length < 2) { setResults([]); return; }
    setSearching(true);
    const data = await api(`/names/search?q=${encodeURIComponent(q)}&limit=30`);
    setResults(data?.results || []);
    setSearching(false);
  }, []);

  const handleInput = (e) => {
    const v = e.target.value;
    setQuery(v);
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(v), 300);
  };

  return (
    <div>
      <div style={{ padding: 16 }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          background: T.card, borderRadius: 10, padding: "10px 14px",
          border: `1px solid ${T.border}`,
        }}>
          <Icon d={Icons.search} size={18} color={T.dim} />
          <input
            value={query}
            onChange={handleInput}
            placeholder="Поиск по имени..."
            style={{
              flex: 1, background: "transparent", border: "none", outline: "none",
              color: T.text, fontSize: 15, fontFamily: "'Cormorant Garamond', serif",
            }}
          />
          {query && (
            <button onClick={() => { setQuery(""); setResults([]); }} style={{
              background: "transparent", border: "none", cursor: "pointer", padding: 0,
            }}>
              <Icon d={Icons.x} size={16} color={T.dim} />
            </button>
          )}
        </div>
      </div>

      <div style={{ padding: "0 16px" }}>
        {searching && <div style={{ color: T.dim, textAlign: "center", padding: 20 }}>Поиск...</div>}
        {!searching && query.length >= 2 && results.length === 0 && (
          <Empty msg={`Ничего не найдено по запросу "${query}"`} />
        )}
        {results.map((r, i) => (
          <div key={r.person_id} style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "10px 14px", background: T.card, borderRadius: 8,
            marginBottom: 6, borderLeft: `3px solid ${T.purple}`,
          }}>
            <div>
              <div style={{ color: T.text, fontSize: 15, fontWeight: 600, fontFamily: "'Cormorant Garamond', serif" }}>
                {r.prefix && <span style={{ color: T.dim, fontSize: 12, fontStyle: "italic", marginRight: 6 }}>{r.prefix}</span>}
                {r.canonical_name}
              </div>
              <div style={{ color: T.dim, fontSize: 10, fontFamily: "'JetBrains Mono', monospace", marginTop: 2 }}>
                {r.method} · score: {r.score.toFixed(2)}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AddPage() {
  const [form, setForm] = useState({
    orderType: "О здравии",
    periodType: "Сорокоуст (40 дней)",
    names: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async () => {
    if (!form.names.trim()) return;
    setSubmitting(true);
    setResult(null);
    const data = await api("/orders", {
      method: "POST",
      body: JSON.stringify({
        order_type: form.orderType,
        period_type: form.periodType,
        names_text: form.names,
      }),
    });
    setResult(data);
    setSubmitting(false);
    if (data?.order_id) {
      setForm(f => ({ ...f, names: "" }));
    }
  };

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ margin: "0 0 16px", color: T.gold, fontSize: 20, fontFamily: "'Cormorant Garamond', serif" }}>
        Новая записка
      </h2>

      {/* Order type */}
      <label style={{ color: T.dim, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", display: "block", marginBottom: 6 }}>
        Тип записки
      </label>
      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {["О здравии", "Об упокоении"].map(t => (
          <button key={t} onClick={() => setForm(f => ({ ...f, orderType: t }))} style={{
            flex: 1, padding: "10px 0", borderRadius: 8, border: "none", cursor: "pointer",
            fontSize: 13, fontWeight: 600, fontFamily: "'Cormorant Garamond', serif",
            background: form.orderType === t
              ? (t === "О здравии" ? T.green : T.red) + "33"
              : T.card,
            color: form.orderType === t
              ? (t === "О здравии" ? T.green : T.red)
              : T.dim,
          }}>{t}</button>
        ))}
      </div>

      {/* Period */}
      <label style={{ color: T.dim, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", display: "block", marginBottom: 6 }}>
        Срок поминовения
      </label>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
        {["Разовое (не выбрано)", "Сорокоуст (40 дней)", "На полгода", "На год"].map(p => (
          <button key={p} onClick={() => setForm(f => ({ ...f, periodType: p }))} style={{
            padding: "10px 8px", borderRadius: 8, border: "none", cursor: "pointer",
            fontSize: 12, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace",
            background: form.periodType === p ? T.gold + "33" : T.card,
            color: form.periodType === p ? T.gold : T.dim,
          }}>{p.replace(" (не выбрано)", "").replace(" (40 дней)", "")}</button>
        ))}
      </div>

      {/* Names textarea */}
      <label style={{ color: T.dim, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", display: "block", marginBottom: 6 }}>
        Имена (через запятую, пробел или перенос строки)
      </label>
      <textarea
        value={form.names}
        onChange={e => setForm(f => ({ ...f, names: e.target.value }))}
        placeholder="Николая, Тамары, Ксении..."
        rows={4}
        style={{
          width: "100%", padding: 12, borderRadius: 8, border: `1px solid ${T.border}`,
          background: T.card, color: T.text, fontSize: 15, resize: "vertical",
          fontFamily: "'Cormorant Garamond', serif", outline: "none", boxSizing: "border-box",
        }}
      />

      <button onClick={handleSubmit} disabled={submitting || !form.names.trim()} style={{
        width: "100%", padding: 14, borderRadius: 10, border: "none",
        background: T.gold, color: T.bg, fontSize: 15, fontWeight: 700,
        cursor: submitting ? "wait" : "pointer", marginTop: 16,
        fontFamily: "'Cormorant Garamond', serif", opacity: submitting ? 0.6 : 1,
      }}>
        {submitting ? "Сохранение..." : "Подать записку"}
      </button>

      {result && result.order_id && (
        <div style={{
          marginTop: 16, padding: 14, borderRadius: 8,
          background: T.green + "15", border: `1px solid ${T.green}44`,
          color: T.green, fontSize: 13, fontFamily: "'JetBrains Mono', monospace",
        }}>
          ✓ Записка #{result.order_id} создана · {result.order_type} · {result.period_type} · до {result.expires_at?.split("T")[0]}
        </div>
      )}
    </div>
  );
}

function UploadPage() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const fileRef = useRef(null);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API}/upload/csv?delimiter=;`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ error: e.message });
    }
    setUploading(false);
  };

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ margin: "0 0 16px", color: T.gold, fontSize: 20, fontFamily: "'Cormorant Garamond', serif" }}>
        Загрузка CSV
      </h2>

      <div
        onClick={() => fileRef.current?.click()}
        style={{
          padding: 40, borderRadius: 12, border: `2px dashed ${T.border}`,
          textAlign: "center", cursor: "pointer", background: T.card,
          transition: "all 0.2s",
        }}
        onDragOver={e => { e.preventDefault(); e.currentTarget.style.borderColor = T.gold; }}
        onDragLeave={e => { e.currentTarget.style.borderColor = T.border; }}
        onDrop={e => { e.preventDefault(); e.currentTarget.style.borderColor = T.border; setFile(e.dataTransfer.files[0]); }}
      >
        <Icon d={Icons.upload} size={36} color={T.dim} />
        <div style={{ color: T.dim, fontSize: 13, marginTop: 10, fontFamily: "'JetBrains Mono', monospace" }}>
          {file ? file.name : "Выберите CSV файл или перетащите сюда"}
        </div>
        <input ref={fileRef} type="file" accept=".csv" style={{ display: "none" }}
          onChange={e => setFile(e.target.files?.[0] || null)} />
      </div>

      {file && (
        <button onClick={handleUpload} disabled={uploading} style={{
          width: "100%", padding: 14, borderRadius: 10, border: "none",
          background: T.gold, color: T.bg, fontSize: 15, fontWeight: 700,
          cursor: uploading ? "wait" : "pointer", marginTop: 16,
          fontFamily: "'Cormorant Garamond', serif", opacity: uploading ? 0.6 : 1,
        }}>
          {uploading ? "Загрузка..." : "Импортировать"}
        </button>
      )}

      {result && (
        <div style={{
          marginTop: 16, padding: 14, borderRadius: 8, fontSize: 13,
          fontFamily: "'JetBrains Mono', monospace",
          background: result.error ? T.red + "15" : T.green + "15",
          border: `1px solid ${result.error ? T.red : T.green}44`,
          color: result.error ? T.red : T.green,
        }}>
          {result.error ? (
            <span>Ошибка: {result.error}</span>
          ) : (
            <div>
              <div>✓ {result.filename}</div>
              <div style={{ marginTop: 6, color: T.text }}>
                Всего: {result.stats?.total} · Импортировано: {result.stats?.imported} · Пропущено: {result.stats?.skipped} · Ошибки: {result.stats?.errors}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatsPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api("/names/stats").then(d => { setStats(d); setLoading(false); });
  }, []);

  if (loading) return <Loading />;

  const s = stats || {};

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ margin: "0 0 16px", color: T.gold, fontSize: 20, fontFamily: "'Cormorant Garamond', serif" }}>
        Статистика
      </h2>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        {[
          { label: "Имён всего", value: s.total_persons, color: T.purple },
          { label: "Записок всего", value: s.total_orders, color: T.blue },
          { label: "Активных записок", value: s.active_orders, color: T.gold },
          { label: "Имён на сегодня", value: s.active_names_today, color: T.green },
        ].map((item, i) => (
          <div key={i} style={{
            padding: 16, borderRadius: 10, background: T.card,
            borderLeft: `3px solid ${item.color}`,
          }}>
            <div style={{ color: item.color, fontSize: 28, fontWeight: 700, fontFamily: "'Cormorant Garamond', serif" }}>
              {item.value ?? "—"}
            </div>
            <div style={{ color: T.dim, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", marginTop: 4 }}>
              {item.label}
            </div>
          </div>
        ))}
      </div>

      {s.by_type && Object.keys(s.by_type).length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h3 style={{ color: T.text, fontSize: 15, fontFamily: "'Cormorant Garamond', serif", marginBottom: 10 }}>
            Активные по типам
          </h3>
          {Object.entries(s.by_type).map(([type, count]) => (
            <div key={type} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "10px 14px", background: T.card, borderRadius: 8, marginBottom: 6,
              borderLeft: `3px solid ${type === "здравие" ? T.green : T.red}`,
            }}>
              <span style={{ color: T.text, fontSize: 14, fontFamily: "'Cormorant Garamond', serif" }}>
                {type === "здравие" ? "О здравии" : "Об упокоении"}
              </span>
              <Badge color={type === "здравие" ? T.green : T.red}>{count}</Badge>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Loading() {
  return (
    <div style={{ padding: 40, textAlign: "center" }}>
      <div style={{
        width: 32, height: 32, border: `3px solid ${T.border}`,
        borderTop: `3px solid ${T.gold}`, borderRadius: "50%",
        animation: "spin 1s linear infinite", margin: "0 auto",
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  );
}

function Empty({ msg }) {
  return (
    <div style={{ padding: 40, textAlign: "center", color: T.dim, fontSize: 13, fontFamily: "'JetBrains Mono', monospace" }}>
      {msg}
    </div>
  );
}

// ─── App Shell ────────────────────────────────────────────

const TABS = [
  { id: "today", label: "Сегодня", icon: Icons.calendar },
  { id: "search", label: "Поиск", icon: Icons.search },
  { id: "add", label: "Записка", icon: Icons.plus },
  { id: "upload", label: "CSV", icon: Icons.upload },
  { id: "stats", label: "Стат.", icon: Icons.bar },
];

export default function SinodikApp() {
  const [tab, setTab] = useState("today");

  return (
    <div style={{
      background: T.bg, color: T.text, minHeight: "100vh",
      fontFamily: "'Cormorant Garamond', serif",
      display: "flex", flexDirection: "column",
      maxWidth: 480, margin: "0 auto",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{
        padding: "14px 16px", display: "flex", alignItems: "center", gap: 10,
        background: T.surface, borderBottom: `1px solid ${T.border}`,
      }}>
        <span style={{ fontSize: 24 }}>☦️</span>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, color: T.gold, letterSpacing: 2 }}>
            СИНОДИК
          </div>
          <div style={{ fontSize: 9, color: T.dim, fontFamily: "'JetBrains Mono', monospace", letterSpacing: 1 }}>
            ЗАПИСКИ ДЛЯ ПОМИНОВЕНИЯ
          </div>
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: "auto", paddingBottom: 70 }}>
        {tab === "today" && <TodayPage />}
        {tab === "search" && <SearchPage />}
        {tab === "add" && <AddPage />}
        {tab === "upload" && <UploadPage />}
        {tab === "stats" && <StatsPage />}
      </div>

      {/* Bottom Tab Bar */}
      <div style={{
        position: "fixed", bottom: 0, left: "50%", transform: "translateX(-50%)",
        width: "100%", maxWidth: 480,
        display: "flex", background: T.surface,
        borderTop: `1px solid ${T.border}`,
        paddingBottom: "env(safe-area-inset-bottom, 8px)",
      }}>
        {TABS.map(t => (
          <Tab key={t.id} active={tab === t.id} label={t.label} icon={t.icon} onClick={() => setTab(t.id)} />
        ))}
      </div>
    </div>
  );
}
