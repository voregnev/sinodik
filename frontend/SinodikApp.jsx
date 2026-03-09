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
  db: "M12 2C7.03 2 3 3.34 3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5c0-1.66-4.03-3-9-3zM3 12c0 1.66 4.03 3 9 3s9-1.34 9-3M3 8c0 1.66 4.03 3 9 3s9-1.34 9-3",
  pencil: "M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z",
  trash: "M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6",
  save: "M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2zM17 21v-8H7v8M7 3v5h8",
};

// ─── Fetch helper (returns null on error) ─────────────────
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

// Like api() but throws on error (returns detail from body when available)
async function apiOrThrow(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    let detail = `${res.status}: ${res.statusText}`;
    try { const b = await res.json(); if (b.detail) detail = b.detail; } catch {}
    throw new Error(detail);
  }
  return res.json();
}

// ─── Shared UI primitives ─────────────────────────────────

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

function NameCard({ name, genitiveName, prefix, suffix, orderType, periodType, expiresAt, position }) {
  const isHealth = orderType === "здравие";
  const color = isHealth ? T.green : T.red;
  const exp = expiresAt ? new Date(expiresAt) : null;
  const daysLeft = exp ? Math.max(0, Math.ceil((exp - new Date()) / 86400000)) : 0;
  // Show genitive if available, otherwise fall back to nominative
  const displayName = genitiveName || name;

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "10px 14px", background: T.card, borderRadius: 8,
      borderLeft: `3px solid ${color}`, marginBottom: 6,
    }}>
      <div>
        <div style={{ color: T.text, fontSize: 15, fontWeight: 600, fontFamily: "'Cormorant Garamond', serif" }}>
          {prefix && <span style={{ color: T.dim, fontSize: 12, fontStyle: "italic", marginRight: 5 }}>{prefix}</span>}
          {displayName}
          {suffix && <span style={{ color: T.dim, fontSize: 12, fontStyle: "italic", marginLeft: 5 }}>{suffix}</span>}
          {position != null && (
            <span style={{ color: T.dim, fontSize: 10, marginLeft: 6, fontFamily: "'JetBrains Mono', monospace" }}>
              #{position}
            </span>
          )}
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

function InputStyle() {
  return {
    width: "100%", padding: "10px 12px", borderRadius: 8,
    border: `1px solid ${T.border}`, background: T.card,
    color: T.text, fontSize: 13, outline: "none",
    boxSizing: "border-box", fontFamily: "'JetBrains Mono', monospace",
  };
}

function LabelStyle() {
  return {
    color: T.dim, fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
    display: "block", marginBottom: 6,
  };
}

// ─── Pages ────────────────────────────────────────────────

const PERIOD_ORDER = ["год", "полгода", "сорокоуст", "разовое"];
const PERIOD_LABELS = {
  "год": "Год",
  "полгода": "Полгода",
  "сорокоуст": "Сорокоуст (40 дней)",
  "разовое": "Разовое",
};

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

  const sections =
    filter === "all"
      ? [{ key: "здравие", names: healthNames }, { key: "упокоение", names: restNames }]
      : filter === "здравие"
        ? [{ key: "здравие", names: healthNames }]
        : [{ key: "упокоение", names: restNames }];

  // Group a flat list by period
  function byPeriod(names) {
    const map = {};
    for (const n of names) {
      const p = n.period_type || "разовое";
      if (!map[p]) map[p] = [];
      map[p].push(n);
    }
    return map;
  }

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

      {/* Names grouped: type → period */}
      <div style={{ padding: "8px 16px" }}>
        {data.total === 0 ? (
          <Empty msg="Нет активных записок на сегодня" />
        ) : (
          sections.map(({ key, names }) => {
            if (!names.length) return null;
            const periodMap = byPeriod(names);
            const isHealth = key === "здравие";
            const typeColor = isHealth ? T.green : T.red;
            const typeLabel = isHealth ? "О здравии" : "Об упокоении";

            return (
              <div key={key} style={{ marginBottom: 20 }}>
                {filter === "all" && (
                  <div style={{
                    color: typeColor, fontSize: 13, fontWeight: 700,
                    fontFamily: "'Cormorant Garamond', serif",
                    borderBottom: `1px solid ${typeColor}33`,
                    paddingBottom: 4, marginBottom: 10,
                    display: "flex", alignItems: "center", gap: 6,
                  }}>
                    {typeLabel} <Badge color={typeColor}>{names.length}</Badge>
                  </div>
                )}
                {PERIOD_ORDER.map(period => {
                  const pNames = periodMap[period];
                  if (!pNames || !pNames.length) return null;
                  return (
                    <div key={period} style={{ marginBottom: 12 }}>
                      <div style={{
                        color: T.dim, fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
                        textTransform: "uppercase", letterSpacing: 1,
                        marginBottom: 6,
                      }}>
                        {PERIOD_LABELS[period] || period}
                      </div>
                      {pNames.map((n, i) => (
                        <NameCard
                          key={`${n.commemoration_id}-${i}`}
                          name={n.canonical_name}
                          genitiveName={n.genitive_name}
                          prefix={n.prefix}
                          suffix={n.suffix}
                          orderType={n.order_type}
                          periodType={null}
                          expiresAt={n.expires_at}
                          position={n.position}
                        />
                      ))}
                    </div>
                  );
                })}
              </div>
            );
          })
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
    startsAt: "",
    needReceipt: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = async () => {
    if (!form.names.trim()) return;
    setSubmitting(true);
    setResult(null);
    setError(null);
    try {
      const data = await apiOrThrow("/orders", {
        method: "POST",
        body: JSON.stringify({
          order_type: form.orderType,
          period_type: form.periodType,
          names_text: form.names,
          starts_at: form.startsAt ? `${form.startsAt}T00:00:00` : null,
          need_receipt: form.needReceipt,
        }),
      });
      setResult(data);
      if (data?.order_id) {
        setForm(f => ({ ...f, names: "", startsAt: "", needReceipt: false }));
      }
    } catch (e) {
      setError(e.message);
    }
    setSubmitting(false);
  };

  const inputSt = InputStyle();
  const labelSt = LabelStyle();

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ margin: "0 0 16px", color: T.gold, fontSize: 20, fontFamily: "'Cormorant Garamond', serif" }}>
        Новая записка
      </h2>

      {/* Order type */}
      <label style={labelSt}>Тип записки</label>
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
      <label style={labelSt}>Срок поминовения</label>
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
      <label style={labelSt}>Имена (через запятую, пробел или перенос строки)</label>
      <textarea
        value={form.names}
        onChange={e => setForm(f => ({ ...f, names: e.target.value }))}
        placeholder="Николая, Тамары, Ксении..."
        rows={4}
        style={{
          ...inputSt, resize: "vertical",
          fontFamily: "'Cormorant Garamond', serif", fontSize: 15,
        }}
      />

      {/* Start date */}
      <label style={{ ...labelSt, marginTop: 12 }}>Дата начала (необязательно)</label>
      <input
        type="date"
        value={form.startsAt}
        onChange={e => setForm(f => ({ ...f, startsAt: e.target.value }))}
        style={inputSt}
      />

      {/* Need receipt */}
      <label style={{
        display: "flex", alignItems: "center", gap: 8, cursor: "pointer",
        marginTop: 12, color: T.dim, fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
      }}>
        <input
          type="checkbox"
          checked={form.needReceipt}
          onChange={e => setForm(f => ({ ...f, needReceipt: e.target.checked }))}
          style={{ width: 16, height: 16, cursor: "pointer" }}
        />
        Нужна квитанция
      </label>

      <button onClick={handleSubmit} disabled={submitting || !form.names.trim()} style={{
        width: "100%", padding: 14, borderRadius: 10, border: "none",
        background: T.gold, color: T.bg, fontSize: 15, fontWeight: 700,
        cursor: submitting ? "wait" : "pointer", marginTop: 16,
        fontFamily: "'Cormorant Garamond', serif", opacity: submitting ? 0.6 : 1,
      }}>
        {submitting ? "Сохранение..." : "Подать записку"}
      </button>

      {error && (
        <div style={{
          marginTop: 12, padding: 12, borderRadius: 8,
          background: T.red + "15", border: `1px solid ${T.red}44`,
          color: T.red, fontSize: 13, fontFamily: "'JetBrains Mono', monospace",
        }}>
          ✗ {error}
        </div>
      )}

      {result && result.order_id && (
        <div style={{
          marginTop: 16, padding: 14, borderRadius: 8,
          background: T.green + "15", border: `1px solid ${T.green}44`,
          color: T.green, fontSize: 13, fontFamily: "'JetBrains Mono', monospace",
        }}>
          ✓ Записка #{result.order_id} создана · {result.commemorations_created} имён
        </div>
      )}
    </div>
  );
}

function UploadPage() {
  const [file, setFile] = useState(null);
  const [startsAt, setStartsAt] = useState("");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [showErrors, setShowErrors] = useState(false);
  const fileRef = useRef(null);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setResult(null);
    setShowErrors(false);

    const formData = new FormData();
    formData.append("file", file);

    let url = `${API}/upload/csv?delimiter=;`;
    if (startsAt) url += `&starts_at=${startsAt}T00:00:00`;

    try {
      const res = await fetch(url, { method: "POST", body: formData });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ error: e.message });
    }
    setUploading(false);
  };

  const inputSt = InputStyle();

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

      {/* Start date for all records */}
      <label style={{ ...LabelStyle(), marginTop: 16 }}>Дата начала для всех записей (необязательно)</label>
      <input
        type="date"
        value={startsAt}
        onChange={e => setStartsAt(e.target.value)}
        style={inputSt}
      />

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
              <div>✓ Импорт завершён</div>
              <div style={{ marginTop: 6, color: T.text }}>
                Всего: {result.total_rows} · Создано: {result.orders_created} · Пропущено: {result.skipped}
                {Array.isArray(result.errors) && result.errors.length > 0 && (
                  <span> · <span
                    style={{ color: T.red, cursor: "pointer", textDecoration: "underline" }}
                    onClick={() => setShowErrors(v => !v)}
                  >
                    Ошибки: {result.errors.length}
                  </span></span>
                )}
              </div>
              {showErrors && Array.isArray(result.errors) && (
                <div style={{ marginTop: 8, padding: 8, background: T.red + "11", borderRadius: 6 }}>
                  {result.errors.map((e, i) => (
                    <div key={i} style={{ color: T.red, fontSize: 11, marginBottom: 4 }}>• {e}</div>
                  ))}
                </div>
              )}
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
          { label: "Активных записей", value: s.total_commemorations, color: T.gold },
          { label: "Имён на сегодня", value: s.active_today, color: T.green },
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

// ─── DB Management Page ───────────────────────────────────

function CommemorationManager() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterNoStart, setFilterNoStart] = useState(false);
  const [bulkDate, setBulkDate] = useState("");
  const [bulkMsg, setBulkMsg] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    const data = await api(`/commemorations?no_start_date=${filterNoStart}&limit=200`);
    setItems(data?.items || []);
    setLoading(false);
  }, [filterNoStart]);

  useEffect(() => { load(); }, [load]);

  const handleBulkUpdate = async () => {
    if (!bulkDate) return;
    setBulkMsg(null);
    try {
      const ids = items.map(i => i.id);
      const res = await apiOrThrow("/commemorations/bulk-update", {
        method: "POST",
        body: JSON.stringify({ ids, starts_at: `${bulkDate}T00:00:00` }),
      });
      setBulkMsg(`✓ Обновлено: ${res.updated}`);
      load();
    } catch (e) {
      setBulkMsg(`✗ ${e.message}`);
    }
  };

  const startEdit = (item) => {
    setEditingId(item.id);
    setEditValues({
      order_type: item.order_type,
      period_type: item.period_type,
      starts_at: item.starts_at ? item.starts_at.slice(0, 10) : "",
      expires_at: item.expires_at ? item.expires_at.slice(0, 10) : "",
      prefix: item.prefix || "",
    });
  };

  const saveEdit = async (id) => {
    try {
      await apiOrThrow(`/commemorations/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          order_type: editValues.order_type || null,
          period_type: editValues.period_type || null,
          starts_at: editValues.starts_at ? `${editValues.starts_at}T00:00:00` : null,
          expires_at: editValues.expires_at ? `${editValues.expires_at}T00:00:00` : null,
          prefix: editValues.prefix || null,
        }),
      });
      setEditingId(null);
      load();
    } catch (e) {
      alert(e.message);
    }
  };

  const inputSt = { ...InputStyle(), padding: "4px 8px", fontSize: 11 };

  return (
    <div>
      {/* Filter */}
      <label style={{
        display: "flex", alignItems: "center", gap: 8, cursor: "pointer",
        color: T.dim, fontSize: 12, fontFamily: "'JetBrains Mono', monospace", marginBottom: 12,
      }}>
        <input
          type="checkbox"
          checked={filterNoStart}
          onChange={e => setFilterNoStart(e.target.checked)}
          style={{ width: 15, height: 15 }}
        />
        Только без даты начала
      </label>

      {/* Bulk update bar */}
      {filterNoStart && (
        <div style={{
          display: "flex", gap: 8, alignItems: "center", marginBottom: 12,
          padding: 10, background: T.card, borderRadius: 8, border: `1px solid ${T.border}`,
        }}>
          <input
            type="date"
            value={bulkDate}
            onChange={e => setBulkDate(e.target.value)}
            style={{ ...inputSt, flex: 1 }}
          />
          <button
            onClick={handleBulkUpdate}
            disabled={!bulkDate || items.length === 0}
            style={{
              padding: "6px 12px", borderRadius: 6, border: "none", cursor: "pointer",
              background: T.gold, color: T.bg, fontSize: 11, fontWeight: 700,
              fontFamily: "'JetBrains Mono', monospace", whiteSpace: "nowrap",
            }}
          >
            Установить всем ({items.length})
          </button>
        </div>
      )}
      {bulkMsg && (
        <div style={{
          color: bulkMsg.startsWith("✓") ? T.green : T.red,
          fontSize: 12, fontFamily: "'JetBrains Mono', monospace", marginBottom: 8,
        }}>
          {bulkMsg}
        </div>
      )}

      {loading ? <Loading /> : (
        <div style={{ fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
          {items.length === 0 && <Empty msg="Нет записей" />}
          {items.map(item => (
            <div key={item.id} style={{
              background: T.card, borderRadius: 8, marginBottom: 6,
              borderLeft: `3px solid ${item.order_type === "здравие" ? T.green : T.red}`,
              padding: "8px 12px",
            }}>
              {editingId === item.id ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                    <span style={{ color: T.dim }}>#{item.id}</span>
                    <span style={{ color: T.text, fontFamily: "'Cormorant Garamond', serif", fontSize: 14 }}>{item.canonical_name}</span>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                    <div>
                      <div style={{ color: T.dim, fontSize: 10, marginBottom: 2 }}>Тип</div>
                      <select
                        value={editValues.order_type}
                        onChange={e => setEditValues(v => ({ ...v, order_type: e.target.value }))}
                        style={{ ...inputSt, width: "100%" }}
                      >
                        <option value="здравие">здравие</option>
                        <option value="упокоение">упокоение</option>
                      </select>
                    </div>
                    <div>
                      <div style={{ color: T.dim, fontSize: 10, marginBottom: 2 }}>Период</div>
                      <select
                        value={editValues.period_type}
                        onChange={e => setEditValues(v => ({ ...v, period_type: e.target.value }))}
                        style={{ ...inputSt, width: "100%" }}
                      >
                        <option value="разовое">разовое</option>
                        <option value="сорокоуст">сорокоуст</option>
                        <option value="полгода">полгода</option>
                        <option value="год">год</option>
                      </select>
                    </div>
                    <div>
                      <div style={{ color: T.dim, fontSize: 10, marginBottom: 2 }}>Начало</div>
                      <input type="date" value={editValues.starts_at}
                        onChange={e => setEditValues(v => ({ ...v, starts_at: e.target.value }))}
                        style={{ ...inputSt, width: "100%" }} />
                    </div>
                    <div>
                      <div style={{ color: T.dim, fontSize: 10, marginBottom: 2 }}>Конец</div>
                      <input type="date" value={editValues.expires_at}
                        onChange={e => setEditValues(v => ({ ...v, expires_at: e.target.value }))}
                        style={{ ...inputSt, width: "100%" }} />
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                    <button onClick={() => setEditingId(null)} style={{
                      padding: "4px 10px", borderRadius: 5, border: `1px solid ${T.border}`,
                      background: "transparent", color: T.dim, cursor: "pointer", fontSize: 11,
                    }}>Отмена</button>
                    <button onClick={() => saveEdit(item.id)} style={{
                      padding: "4px 10px", borderRadius: 5, border: "none",
                      background: T.gold, color: T.bg, cursor: "pointer", fontSize: 11, fontWeight: 700,
                    }}>Сохранить</button>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <span style={{ color: T.dim, marginRight: 6 }}>#{item.id}</span>
                    <span style={{ color: T.text, fontFamily: "'Cormorant Garamond', serif", fontSize: 14 }}>
                      {item.prefix ? `${item.prefix} ` : ""}{item.canonical_name}
                    </span>
                    <div style={{ color: T.dim, fontSize: 10, marginTop: 2 }}>
                      {item.order_type} · {item.period_type}
                      {item.starts_at ? ` · c ${item.starts_at.slice(0, 10)}` : " · без даты начала"}
                      {item.position != null ? ` · #${item.position}` : ""}
                    </div>
                  </div>
                  <button onClick={() => startEdit(item)} style={{
                    background: "transparent", border: "none", cursor: "pointer", padding: 4,
                  }}>
                    <Icon d={Icons.pencil} size={14} color={T.dim} />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function OrderManager() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    const data = await api("/orders?limit=200");
    setOrders(data || []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const startEdit = (order) => {
    setEditingId(order.id);
    setEditValues({
      user_email: order.user_email || "",
      ordered_at: order.ordered_at ? order.ordered_at.slice(0, 10) : "",
      need_receipt: order.need_receipt || false,
    });
  };

  const saveEdit = async (id) => {
    try {
      await apiOrThrow(`/orders/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          user_email: editValues.user_email || null,
          ordered_at: editValues.ordered_at ? `${editValues.ordered_at}T00:00:00` : null,
          need_receipt: editValues.need_receipt,
        }),
      });
      setEditingId(null);
      load();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm(`Удалить записку #${id}? Имена останутся в базе.`)) return;
    try {
      await apiOrThrow(`/orders/${id}`, { method: "DELETE" });
      load();
    } catch (e) {
      alert(e.message);
    }
  };

  const inputSt = { ...InputStyle(), padding: "4px 8px", fontSize: 11 };

  return (
    <div>
      {loading ? <Loading /> : (
        <div style={{ fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
          {orders.length === 0 && <Empty msg="Нет записей" />}
          {orders.map(order => (
            <div key={order.id} style={{
              background: T.card, borderRadius: 8, marginBottom: 6,
              borderLeft: `3px solid ${T.gold}`, padding: "8px 12px",
            }}>
              {editingId === order.id ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <div style={{ color: T.dim, fontSize: 11 }}>
                    Записка #{order.id} · {order.source_channel}
                  </div>
                  <div>
                    <div style={{ color: T.dim, fontSize: 10, marginBottom: 2 }}>Email</div>
                    <input
                      type="email"
                      value={editValues.user_email}
                      onChange={e => setEditValues(v => ({ ...v, user_email: e.target.value }))}
                      placeholder="не указан"
                      style={{ ...inputSt, width: "100%" }}
                    />
                  </div>
                  <div>
                    <div style={{ color: T.dim, fontSize: 10, marginBottom: 2 }}>Дата заказа</div>
                    <input type="date" value={editValues.ordered_at}
                      onChange={e => setEditValues(v => ({ ...v, ordered_at: e.target.value }))}
                      style={{ ...inputSt, width: "100%" }} />
                  </div>
                  <label style={{
                    display: "flex", alignItems: "center", gap: 6,
                    color: T.dim, fontSize: 11, cursor: "pointer",
                  }}>
                    <input type="checkbox" checked={editValues.need_receipt}
                      onChange={e => setEditValues(v => ({ ...v, need_receipt: e.target.checked }))} />
                    Нужна квитанция
                  </label>
                  <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                    <button onClick={() => setEditingId(null)} style={{
                      padding: "4px 10px", borderRadius: 5, border: `1px solid ${T.border}`,
                      background: "transparent", color: T.dim, cursor: "pointer", fontSize: 11,
                    }}>Отмена</button>
                    <button onClick={() => saveEdit(order.id)} style={{
                      padding: "4px 10px", borderRadius: 5, border: "none",
                      background: T.gold, color: T.bg, cursor: "pointer", fontSize: 11, fontWeight: 700,
                    }}>Сохранить</button>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <span style={{ color: T.dim, marginRight: 6 }}>#{order.id}</span>
                    <span style={{ color: T.text }}>{order.user_email || "—"}</span>
                    {order.need_receipt && <Badge color={T.blue} style={{ marginLeft: 6 }}>квитанция</Badge>}
                    <div style={{ color: T.dim, fontSize: 10, marginTop: 2 }}>
                      {order.source_channel}
                      {order.ordered_at ? ` · ${order.ordered_at.slice(0, 10)}` : ""}
                      {order.created_at ? ` · создана ${order.created_at.slice(0, 10)}` : ""}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 4 }}>
                    <button onClick={() => startEdit(order)} style={{
                      background: "transparent", border: "none", cursor: "pointer", padding: 4,
                    }}>
                      <Icon d={Icons.pencil} size={14} color={T.dim} />
                    </button>
                    <button onClick={() => handleDelete(order.id)} style={{
                      background: "transparent", border: "none", cursor: "pointer", padding: 4,
                    }}>
                      <Icon d={Icons.trash} size={14} color={T.red + "aa"} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DbManagePage() {
  const [section, setSection] = useState("commemorations");

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ margin: "0 0 12px", color: T.gold, fontSize: 20, fontFamily: "'Cormorant Garamond', serif" }}>
        База данных
      </h2>

      <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
        {[
          { id: "commemorations", label: "Поминовения" },
          { id: "orders", label: "Записки" },
        ].map(s => (
          <button key={s.id} onClick={() => setSection(s.id)} style={{
            flex: 1, padding: "8px 0", borderRadius: 8, border: "none", cursor: "pointer",
            fontSize: 12, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace",
            background: section === s.id ? T.gold + "33" : T.card,
            color: section === s.id ? T.gold : T.dim,
          }}>{s.label}</button>
        ))}
      </div>

      {section === "commemorations" && <CommemorationManager />}
      {section === "orders" && <OrderManager />}
    </div>
  );
}

// ─── Utilities ────────────────────────────────────────────

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
  { id: "db", label: "БД", icon: Icons.db },
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
        {tab === "db" && <DbManagePage />}
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
