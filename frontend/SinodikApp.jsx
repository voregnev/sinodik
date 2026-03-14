import { useState, useEffect, useCallback, useRef } from "react";

const API = "/api/v1";
const AUTH_KEY = "sinodik_token";
const authRef = { current: null };

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
  fileText: "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8",
};

// ─── Fetch helper (returns null on error) ─────────────────
async function api(path, opts = {}) {
  try {
    const headers = { "Content-Type": "application/json", ...opts.headers };
    if (authRef.current?.token) headers.Authorization = `Bearer ${authRef.current.token}`;
    const res = await fetch(`${API}${path}`, { ...opts, headers });
    if (res.status === 401) {
      localStorage.removeItem(AUTH_KEY);
      authRef.current?.setToken?.(null);
      authRef.current?.setUser?.(null);
      return null;
    }
    if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`);
    return await res.json();
  } catch (e) {
    console.error("API error:", e);
    return null;
  }
}

// Like api() but throws on error (returns detail from body when available)
async function apiOrThrow(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...opts.headers };
  if (authRef.current?.token) headers.Authorization = `Bearer ${authRef.current.token}`;
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status === 401) {
    localStorage.removeItem(AUTH_KEY);
    authRef.current?.setToken?.(null);
    authRef.current?.setUser?.(null);
    let detail = "401: Unauthorized";
    try { const b = await res.json(); if (b.detail) detail = b.detail; } catch {}
    throw new Error(detail);
  }
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

function NameCard({ name, genitiveName, prefix, suffix, orderType, periodType, expiresAt, position, showPosition = true, showTypeBadge = true }) {
  const isHealth = orderType === "здравие";
  const color = isHealth ? T.green : T.red;
  const exp = expiresAt ? new Date(expiresAt) : null;
  const daysLeft = exp ? Math.max(0, Math.ceil((exp - new Date()) / 86400000)) : 0;
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
          {showPosition && position != null && (
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
      {showTypeBadge && <Badge color={color}>{isHealth ? "здр." : "уп."}</Badge>}
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
      <div style={{ padding: "16px 16px 8px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
        <div>
          <h2 style={{ margin: 0, color: T.gold, fontSize: 20, fontFamily: "'Cormorant Garamond', serif" }}>
            Имена на сегодня
          </h2>
          <div style={{ color: T.dim, fontSize: 12, fontFamily: "'JetBrains Mono', monospace", marginTop: 2 }}>
            {data.date} · {data.total} имён
          </div>
        </div>
        <a
          href={`${API}/names/today.pdf`}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            padding: "8px 14px", borderRadius: 8, border: `1px solid ${T.gold}44`,
            background: T.gold + "22", color: T.gold, textDecoration: "none",
            fontSize: 12, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace",
            cursor: "pointer",
          }}
        >
          <Icon d={Icons.fileText} size={18} color={T.gold} />
          Скачать PDF
        </a>
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
                          showPosition={false}
                          showTypeBadge={false}
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
  const INITIAL_NAME_FIELDS = 5;
  const [form, setForm] = useState({
    orderType: "О здравии",
    periodType: "Сорокоуст (40 дней)",
    nameFields: Array(INITIAL_NAME_FIELDS).fill(""),
    startsAt: "",
    notifyAccept: false,
    userEmail: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [suggestionsForIndex, setSuggestionsForIndex] = useState(null);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const suggestTimerRef = useRef(null);
  const lastFieldRef = useRef(null);
  const [activeSuggestion, setActiveSuggestion] = useState(-1);

  const fetchSuggestions = useCallback(async (q) => {
    if (!q || q.trim().length < 2) {
      setSuggestions([]);
      setActiveSuggestion(-1);
      return;
    }
    setSuggestionsLoading(true);
    const data = await api(`/persons?limit=20&q=${encodeURIComponent(q.trim())}`);
    setSuggestions(data?.items || []);
    setActiveSuggestion(data?.items?.length ? 0 : -1);
    setSuggestionsLoading(false);
  }, []);

  const updateNameField = (index, value) => {
    setForm(f => {
      const next = [...f.nameFields];
      next[index] = value;
      return { ...f, nameFields: next };
    });
    setSuggestionsForIndex(index);
    if (suggestTimerRef.current) clearTimeout(suggestTimerRef.current);
    if (value.trim().length >= 2) {
      suggestTimerRef.current = setTimeout(() => fetchSuggestions(value), 250);
    } else {
      setSuggestions([]);
      setActiveSuggestion(-1);
    }
  };

  const selectSuggestion = (index, person) => {
    const displayName = person.genitive_name || person.canonical_name;
    setForm(f => {
      const next = [...f.nameFields];
      next[index] = displayName;
      return { ...f, nameFields: next };
    });
    setSuggestions([]);
    setSuggestionsForIndex(null);
    setActiveSuggestion(-1);
  };

  const addNameField = () => {
    setForm(f => ({ ...f, nameFields: [...f.nameFields, ""] }));
    setTimeout(() => {
      lastFieldRef.current?.focus();
    }, 80);
  };

  const handleSubmit = async () => {
    const namesText = form.nameFields.map(s => s.trim()).filter(Boolean).join(", ");
    if (!namesText) return;
    if (form.notifyAccept && !form.userEmail.trim()) {
      setError("Укажите email для уведомления о принятии");
      return;
    }
    setSubmitting(true);
    setResult(null);
    setError(null);
    try {
      const data = await apiOrThrow("/orders", {
        method: "POST",
        body: JSON.stringify({
          order_type: form.orderType,
          period_type: form.periodType,
          names_text: namesText,
          starts_at: form.startsAt ? `${form.startsAt}T00:00:00` : null,
          need_receipt: form.notifyAccept,
          user_email: form.notifyAccept ? form.userEmail.trim() || null : null,
        }),
      });
      setResult(data);
      if (data?.order_id) {
        setForm(f => ({
          ...f,
          nameFields: Array(INITIAL_NAME_FIELDS).fill(""),
          startsAt: "",
          notifyAccept: false,
          userEmail: "",
        }));
      }
    } catch (e) {
      setError(e.message);
    }
    setSubmitting(false);
  };

  const hasNames = form.nameFields.some(s => s.trim().length > 0);
  const canSubmit = hasNames && (!form.notifyAccept || form.userEmail.trim());

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

      {/* Имена: отдельные поля с автодополнением из словаря */}
      <label style={labelSt}>Имена (из словаря или своё)</label>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {form.nameFields.map((value, index) => {
          const isLast = index === form.nameFields.length - 1;
          const showSuggestions = suggestionsForIndex === index && suggestions.length > 0;
          return (
            <div key={index} style={{ position: "relative" }}>
              <input
                ref={isLast ? lastFieldRef : undefined}
                type="text"
                value={value}
                onChange={e => updateNameField(index, e.target.value)}
                onFocus={() => {
                  setSuggestionsForIndex(index);
                }}
                onKeyDown={e => {
                  if (suggestionsForIndex === index && suggestions.length) {
                    if (e.key === "ArrowDown") {
                      e.preventDefault();
                      setActiveSuggestion(prev => {
                        const next = prev + 1;
                        return next >= suggestions.length ? 0 : next;
                      });
                    } else if (e.key === "ArrowUp") {
                      e.preventDefault();
                      setActiveSuggestion(prev => {
                        const next = prev - 1;
                        return next < 0 ? suggestions.length - 1 : next;
                      });
                    } else if (e.key === "Enter") {
                      if (suggestions.length) {
                        e.preventDefault();
                        const idx = activeSuggestion >= 0 ? activeSuggestion : 0;
                        selectSuggestion(index, suggestions[idx]);
                      }
                    } else if (e.key === "Escape") {
                      setSuggestions([]);
                      setSuggestionsForIndex(null);
                      setActiveSuggestion(-1);
                    }
                  }
                }}
                onBlur={() => {
                  setTimeout(() => setSuggestions([]), 150);
                }}
                placeholder={`Имя ${index + 1}`}
                style={{
                  ...inputSt,
                  fontFamily: "'Cormorant Garamond', serif",
                  fontSize: 15,
                  paddingRight: suggestionsLoading ? 32 : 10,
                }}
              />
              {suggestionsForIndex === index && suggestionsLoading && (
                <span style={{
                  position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)",
                  color: T.dim, fontSize: 10,
                }}>…</span>
              )}
              {showSuggestions && (
                <div style={{
                  position: "absolute", left: 0, right: 0, top: "100%", zIndex: 10,
                  marginTop: 2, maxHeight: 160, overflow: "auto",
                  background: T.card, border: `1px solid ${T.border}`, borderRadius: 8,
                  boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                }}>
                  {suggestions.map((p, sIdx) => (
                    <button
                      key={p.id}
                      type="button"
                      onMouseDown={e => { e.preventDefault(); selectSuggestion(index, p); }}
                      style={{
                        width: "100%", textAlign: "left", padding: "8px 12px",
                        background: activeSuggestion === sIdx ? T.gold + "33" : "transparent",
                        border: "none", cursor: "pointer",
                        color: T.text, fontSize: 14, fontFamily: "'Cormorant Garamond', serif",
                        borderBottom: `1px solid ${T.border}`,
                      }}
                    >
                      {p.genitive_name || p.canonical_name}
                      {p.canonical_name !== (p.genitive_name || p.canonical_name) && (
                        <span style={{ color: T.dim, fontSize: 12, marginLeft: 6 }}>
                          ({p.canonical_name})
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
        {form.nameFields.length >= INITIAL_NAME_FIELDS && (
          <button
            type="button"
            onClick={addNameField}
            style={{
              marginTop: 4,
              alignSelf: "flex-start",
              padding: "4px 10px",
              borderRadius: 6,
              border: `1px dashed ${T.border}`,
              background: "transparent",
              color: T.dim,
              cursor: "pointer",
              fontSize: 11,
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            + Добавить имя
          </button>
        )}
      </div>

      {/* Start date */}
      <label style={{ ...labelSt, marginTop: 12 }}>Дата начала (необязательно)</label>
      <input
        type="date"
        value={form.startsAt}
        onChange={e => setForm(f => ({ ...f, startsAt: e.target.value }))}
        style={inputSt}
      />

      {/* Notify about acceptance */}
      <label style={{
        display: "flex", alignItems: "center", gap: 8, cursor: "pointer",
        marginTop: 12, color: T.dim, fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
      }}>
        <input
          type="checkbox"
          checked={form.notifyAccept}
          onChange={e => setForm(f => ({ ...f, notifyAccept: e.target.checked }))}
          style={{ width: 16, height: 16, cursor: "pointer" }}
        />
        Уведомить
      </label>

      {form.notifyAccept && (
        <>
          <label style={{ ...labelSt, marginTop: 8 }}>
            Email <span style={{ color: T.red }}>*</span>
          </label>
          <input
            type="email"
            value={form.userEmail}
            onChange={e => setForm(f => ({ ...f, userEmail: e.target.value }))}
            placeholder="example@mail.ru"
            style={{ ...inputSt, marginTop: 4 }}
          />
        </>
      )}

      <button onClick={handleSubmit} disabled={submitting || !canSubmit} style={{
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

// ─── My Orders (authenticated user) ───────────────────────

function MyOrdersPage() {
  const [orders, setOrders] = useState([]);
  const [byUser, setByUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      api("/orders"),
      api("/names/by-user?active_only=false"),
    ]).then(([ordersData, byUserData]) => {
      if (cancelled) return;
      setOrders(Array.isArray(ordersData) ? ordersData : []);
      setByUser(byUserData);
      setLoading(false);
    }).catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <Loading />;

  const comms = byUser?.commemorations || [];
  const byOrderId = {};
  for (const c of comms) {
    const oid = c.order_id;
    if (!byOrderId[oid]) byOrderId[oid] = [];
    byOrderId[oid].push(c);
  }

  const orderCards = orders.map(order => {
    const group = byOrderId[order.id] || [];
    const orderType = group[0]?.order_type || "здравие";
    const periodType = group[0]?.period_type || "разовое";
    let expiresAt = null;
    for (const c of group) {
      if (c.expires_at) {
        const d = new Date(c.expires_at);
        if (!expiresAt || d > expiresAt) expiresAt = d;
      }
    }
    const names = group.map(c => c.canonical_name).filter(Boolean);
    const isHealth = orderType === "здравие";
    const color = isHealth ? T.green : T.red;

    return (
      <div
        key={order.id}
        style={{
          background: T.card,
          borderRadius: 10,
          marginBottom: 10,
          borderLeft: `4px solid ${color}`,
          padding: "12px 14px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 6 }}>
          <Badge color={color}>{isHealth ? "здравие" : "упокоение"}</Badge>
          <span style={{ color: T.dim, fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
            {PERIOD_LABELS[periodType] || periodType}
          </span>
        </div>
        {expiresAt && (
          <div style={{ color: T.dim, fontSize: 11, marginTop: 4, fontFamily: "'JetBrains Mono', monospace" }}>
            Окончание: {expiresAt.toLocaleDateString("ru-RU")}
          </div>
        )}
        <div style={{ color: T.text, fontSize: 13, marginTop: 6, fontFamily: "'Cormorant Garamond', serif" }}>
          {names.length > 0 ? names.slice(0, 5).join(", ") + (names.length > 5 ? ` и ещё ${names.length - 5}` : "") : `${group.length} имён`}
        </div>
      </div>
    );
  });

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ margin: "0 0 12px", color: T.gold, fontSize: 20, fontFamily: "'Cormorant Garamond', serif" }}>
        Записки
      </h2>
      {orderCards.length === 0 ? (
        <div style={{ padding: 24 }} />
      ) : (
        <div>{orderCards}</div>
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
      suffix: item.suffix || "",
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
          prefix: editValues.prefix !== undefined ? (editValues.prefix || null) : undefined,
          suffix: editValues.suffix !== undefined ? (editValues.suffix || null) : undefined,
        }),
      });
      setEditingId(null);
      load();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleDeleteCommemoration = async (id) => {
    try {
      await apiOrThrow(`/commemorations/${id}`, { method: "DELETE" });
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
                  <div style={{ color: T.dim, fontSize: 10, marginBottom: 2 }}>Префикс · Имя · Суффикс</div>
                  <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                    <input
                      placeholder="в., нпр., мл."
                      value={editValues.prefix}
                      onChange={e => setEditValues(v => ({ ...v, prefix: e.target.value }))}
                      style={{ ...inputSt, flex: "1 1 80px", minWidth: 0 }}
                    />
                    <span style={{ color: T.text, fontFamily: "'Cormorant Garamond', serif", fontSize: 14, flex: "0 0 auto" }}>
                      {item.canonical_name}
                    </span>
                    <input
                      placeholder="со чадом"
                      value={editValues.suffix}
                      onChange={e => setEditValues(v => ({ ...v, suffix: e.target.value }))}
                      style={{ ...inputSt, flex: "1 1 80px", minWidth: 0 }}
                    />
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
                  <div style={{ display: "flex", gap: 6, justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button onClick={() => setEditingId(null)} style={{
                        padding: "4px 10px", borderRadius: 5, border: `1px solid ${T.border}`,
                        background: "transparent", color: T.dim, cursor: "pointer", fontSize: 11,
                      }}>Отмена</button>
                      <button onClick={() => saveEdit(item.id)} style={{
                        padding: "4px 10px", borderRadius: 5, border: "none",
                        background: T.gold, color: T.bg, cursor: "pointer", fontSize: 11, fontWeight: 700,
                      }}>Сохранить</button>
                    </div>
                    <button
                      onClick={() => handleDeleteCommemoration(item.id)}
                      title="Удалить запись"
                      style={{
                        padding: 4, borderRadius: 5, border: "none",
                        background: "transparent", cursor: "pointer",
                      }}
                    >
                      <Icon d={Icons.trash} size={16} color={T.red} />
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <span style={{ color: T.dim, marginRight: 6 }}>#{item.id}</span>
                    <span style={{ color: T.dim, fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
                      {item.prefix ? item.prefix : "—"}
                    </span>
                    <span style={{ color: T.text, fontFamily: "'Cormorant Garamond', serif", fontSize: 14, margin: "0 6px" }}>
                      {item.canonical_name}
                    </span>
                    <span style={{ color: T.dim, fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
                      {item.suffix ? item.suffix : ""}
                    </span>
                    <div style={{ color: T.dim, fontSize: 10, marginTop: 2 }}>
                      {item.order_type} · {item.period_type}
                      {item.starts_at ? ` · c ${item.starts_at.slice(0, 10)}` : " · без даты начала"}
                      {item.position != null ? ` · #${item.position}` : ""}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 4 }}>
                    <button onClick={() => startEdit(item)} title="Редактировать" style={{
                      background: "transparent", border: "none", cursor: "pointer", padding: 4,
                    }}>
                      <Icon d={Icons.pencil} size={14} color={T.dim} />
                    </button>
                    <button onClick={() => handleDeleteCommemoration(item.id)} title="Удалить запись" style={{
                      background: "transparent", border: "none", cursor: "pointer", padding: 4,
                    }}>
                      <Icon d={Icons.trash} size={14} color={T.red} />
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

function OrderManager() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [orderDetail, setOrderDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const data = await api("/orders?limit=200");
    setOrders(data || []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const startEdit = async (order) => {
    setEditingId(order.id);
    setOrderDetail(null);
    setDetailLoading(true);
    setEditValues({
      user_email: order.user_email || "",
      ordered_at: order.ordered_at ? order.ordered_at.slice(0, 10) : "",
      need_receipt: order.need_receipt || false,
    });
    const full = await api(`/orders/${order.id}`);
    setOrderDetail(full);
    setDetailLoading(false);
  };

  const saveEdit = async (id) => {
    if (editValues.need_receipt && !editValues.user_email?.trim()) {
      alert("При включённом «Уведомить» укажите email.");
      return;
    }
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
      setOrderDetail(null);
      load();
    } catch (e) {
      alert(e.message);
    }
  };

  const closeEdit = () => {
    setEditingId(null);
    setOrderDetail(null);
  };

  const handleDelete = async (id) => {
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
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", color: T.dim, fontSize: 11 }}>
                    <div>
                      Записка #{order.id} · {orderDetail?.source_channel ?? order.source_channel}
                    </div>
                    <button
                      onClick={() => handleDelete(order.id)}
                      style={{ background: "transparent", border: "none", cursor: "pointer", padding: 4 }}
                      title="Удалить записку"
                    >
                      <Icon d={Icons.trash} size={14} color={T.red + "aa"} />
                    </button>
                  </div>

                  {/* Все поля заказа (только для чтения, кроме редактируемых) */}
                  <div style={{
                    display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8,
                    padding: 10, background: T.bg, borderRadius: 8, border: `1px solid ${T.border}`,
                  }}>
                    <div><span style={{ color: T.dim, fontSize: 10 }}>ID</span><div style={{ color: T.text, fontSize: 12 }}>{order.id}</div></div>
                    <div><span style={{ color: T.dim, fontSize: 10 }}>Канал</span><div style={{ color: T.text, fontSize: 12 }}>{orderDetail?.source_channel ?? order.source_channel}</div></div>
                    <div><span style={{ color: T.dim, fontSize: 10 }}>external_id</span><div style={{ color: T.text, fontSize: 12 }}>{orderDetail?.external_id ?? order.external_id ?? "—"}</div></div>
                    <div><span style={{ color: T.dim, fontSize: 10 }}>Создана</span><div style={{ color: T.text, fontSize: 12 }}>{orderDetail?.created_at?.slice(0, 10) ?? order.created_at?.slice(0, 10) ?? "—"}</div></div>
                  </div>

                  {/* Исходный текст */}
                  {(orderDetail?.source_raw != null && orderDetail.source_raw !== "") && (
                    <div>
                      <div style={{ color: T.dim, fontSize: 10, marginBottom: 4 }}>Исходный текст</div>
                      <pre style={{
                        margin: 0, padding: 10, background: T.bg, borderRadius: 8, border: `1px solid ${T.border}`,
                        color: T.text, fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word",
                        fontFamily: "'JetBrains Mono', monospace", maxHeight: 120, overflow: "auto",
                      }}>
                        {orderDetail.source_raw}
                      </pre>
                    </div>
                  )}

                  {/* Редактируемые поля */}
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
                    Уведомить
                  </label>
                  {editValues.need_receipt && (
                    <div style={{ marginTop: -4 }}>
                      <div style={{ color: T.dim, fontSize: 10, marginBottom: 2 }}>
                        Email <span style={{ color: T.red }}>*</span>
                      </div>
                      <input
                        type="email"
                        value={editValues.user_email}
                        onChange={e => setEditValues(v => ({ ...v, user_email: e.target.value }))}
                        placeholder="обязательно для уведомления"
                        style={{ ...inputSt, width: "100%", borderColor: !editValues.user_email?.trim() ? T.red + "88" : undefined }}
                      />
                    </div>
                  )}

                  {/* Список извлечённых имён */}
                  {detailLoading ? (
                    <div style={{ color: T.dim, fontSize: 11 }}>Загрузка имён…</div>
                  ) : orderDetail?.commemorations?.length > 0 ? (
                    <div>
                      <div style={{ color: T.dim, fontSize: 10, marginBottom: 6 }}>
                        Извлечённые имена ({orderDetail.commemorations.length})
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 200, overflow: "auto" }}>
                        {orderDetail.commemorations.map((c, idx) => (
                          <div key={c.id} style={{
                            display: "flex", alignItems: "center", gap: 6,
                            padding: "6px 10px", background: T.bg, borderRadius: 6,
                            borderLeft: `3px solid ${c.order_type === "здравие" ? T.green : T.red}`,
                          }}>
                            {c.position != null && (
                              <span style={{ color: T.dim, fontSize: 10, minWidth: 20 }}>#{c.position}</span>
                            )}
                            {c.prefix && <span style={{ color: T.dim, fontSize: 11, fontStyle: "italic" }}>{c.prefix}</span>}
                            <span style={{ color: T.text, fontFamily: "'Cormorant Garamond', serif", fontSize: 14 }}>
                              {c.genitive_name || c.canonical_name}
                            </span>
                            {c.suffix && <span style={{ color: T.dim, fontSize: 11, fontStyle: "italic" }}>{c.suffix}</span>}
                            <span style={{ marginLeft: "auto", fontSize: 10, color: T.dim }}>
                              {c.order_type} · {c.period_type}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : orderDetail && !detailLoading ? (
                    <div style={{ color: T.dim, fontSize: 11 }}>Нет извлечённых имён</div>
                  ) : null}

                  <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                    <button onClick={closeEdit} style={{
                      padding: "4px 10px", borderRadius: 5, border: `1px solid ${T.border}`,
                      background: "transparent", color: T.dim, cursor: "pointer", fontSize: 11,
                    }}>Отмена</button>
                    <button
                      onClick={() => saveEdit(order.id)}
                      disabled={editValues.need_receipt && !editValues.user_email?.trim()}
                      style={{
                        padding: "4px 10px", borderRadius: 5, border: "none",
                        background: T.gold, color: T.bg, cursor: "pointer", fontSize: 11, fontWeight: 700,
                        opacity: editValues.need_receipt && !editValues.user_email?.trim() ? 0.5 : 1,
                      }}
                    >Сохранить</button>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <span style={{ color: T.dim, marginRight: 6 }}>#{order.id}</span>
                    <span style={{ color: T.text }}>{order.user_email || "—"}</span>
                    {order.need_receipt && <Badge color={T.blue} style={{ marginLeft: 6 }}>уведомить</Badge>}
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

function PersonManager() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editValues, setEditValues] = useState({});
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const q = search.trim() ? `&q=${encodeURIComponent(search.trim())}` : "";
    const data = await api(`/persons?limit=200${q}`);
    if (data) {
      setItems(data.items || []);
      setTotal(data.total ?? data.items?.length ?? 0);
    }
    setLoading(false);
  }, [search]);

  useEffect(() => { load(); }, [load]);

  const startEdit = (p) => {
    setEditingId(p.id);
    setEditValues({
      canonical_name: p.canonical_name || "",
      genitive_name: p.genitive_name ?? "",
      gender: p.gender ?? "",
      name_variants: (p.name_variants || []).join(", "),
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditValues({});
    setError(null);
  };

  const saveEdit = async (id) => {
    setError(null);
    const canonical = editValues.canonical_name?.trim();
    if (!canonical) {
      setError("Имя (именительный падеж) не может быть пустым.");
      return;
    }
    const variantsStr = editValues.name_variants || "";
    const name_variants = variantsStr.split(/[,;]/).map(s => s.trim()).filter(Boolean);
    try {
      await apiOrThrow(`/persons/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          canonical_name: canonical,
          genitive_name: editValues.genitive_name?.trim() || null,
          gender: editValues.gender?.trim() || null,
          name_variants,
        }),
      });
      setEditingId(null);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const handleDelete = async (id, canonicalName) => {
    setError(null);
    try {
      await apiOrThrow(`/persons/${id}`, { method: "DELETE" });
      setEditingId(null);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const inputSt = { ...InputStyle(), padding: "6px 10px", fontSize: 12 };

  return (
    <div>
      <div style={{ marginBottom: 12, display: "flex", gap: 8, alignItems: "center" }}>
        <input
          type="text"
          placeholder="Поиск по имени..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={e => e.key === "Enter" && load()}
          style={{ ...inputSt, flex: 1, maxWidth: 280 }}
        />
        <button onClick={load} style={{
          padding: "6px 14px", borderRadius: 8, border: "none", cursor: "pointer",
          background: T.gold, color: T.bg, fontSize: 12, fontWeight: 600,
          fontFamily: "'JetBrains Mono', monospace",
        }}>Найти</button>
      </div>
      {error && (
        <div style={{ color: T.red, fontSize: 12, marginBottom: 8 }}>✗ {error}</div>
      )}
      <div style={{ color: T.dim, fontSize: 11, marginBottom: 8 }}>
        Всего записей: {total}
      </div>
      {loading ? <Loading /> : (
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
          {items.length === 0 && <Empty msg="Нет записей" />}
          {items.map(p => (
            <div key={p.id} style={{
              background: T.card, borderRadius: 8, marginBottom: 6,
              borderLeft: `3px solid ${T.purple}`, padding: "10px 12px",
            }}>
              {editingId === p.id ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <div>
                    <div style={{ color: T.dim, fontSize: 10, marginBottom: 2 }}>Имя (именительный)</div>
                    <input
                      value={editValues.canonical_name}
                      onChange={e => setEditValues(v => ({ ...v, canonical_name: e.target.value }))}
                      style={{ ...inputSt, width: "100%" }}
                      placeholder="Николай"
                    />
                  </div>
                  <div>
                    <div style={{ color: T.dim, fontSize: 10, marginBottom: 2 }}>Родительный падеж</div>
                    <input
                      value={editValues.genitive_name}
                      onChange={e => setEditValues(v => ({ ...v, genitive_name: e.target.value }))}
                      style={{ ...inputSt, width: "100%" }}
                      placeholder="Николая"
                    />
                  </div>
                  <div>
                    <div style={{ color: T.dim, fontSize: 10, marginBottom: 2 }}>Пол</div>
                    <select
                      value={editValues.gender}
                      onChange={e => setEditValues(v => ({ ...v, gender: e.target.value }))}
                      style={{ ...inputSt, width: "100%" }}
                    >
                      <option value="">—</option>
                      <option value="м">м</option>
                      <option value="ж">ж</option>
                    </select>
                  </div>
                  <div>
                    <div style={{ color: T.dim, fontSize: 10, marginBottom: 2 }}>Варианты написания (через запятую)</div>
                    <input
                      value={editValues.name_variants}
                      onChange={e => setEditValues(v => ({ ...v, name_variants: e.target.value }))}
                      style={{ ...inputSt, width: "100%" }}
                      placeholder="Николая, Николай"
                    />
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={cancelEdit} style={{
                      padding: "6px 12px", borderRadius: 6, border: `1px solid ${T.border}`,
                      background: "transparent", color: T.dim, cursor: "pointer", fontSize: 11,
                    }}>Отмена</button>
                    <button onClick={() => saveEdit(p.id)} style={{
                      padding: "6px 12px", borderRadius: 6, border: "none",
                      background: T.gold, color: T.bg, cursor: "pointer", fontSize: 11, fontWeight: 700,
                    }}>Сохранить</button>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                  <div>
                    <span style={{ color: T.dim, marginRight: 8 }}>#{p.id}</span>
                    <span style={{ color: T.text, fontFamily: "'Cormorant Garamond', serif", fontSize: 16 }}>
                      {p.canonical_name}
                    </span>
                    {p.genitive_name && (
                      <span style={{ color: T.dim, marginLeft: 8, fontSize: 12 }}>({p.genitive_name})</span>
                    )}
                    {p.gender && <Badge color={T.purple} style={{ marginLeft: 8 }}>{p.gender}</Badge>}
                    {p.name_variants?.length > 0 && (
                      <div style={{ color: T.dim, fontSize: 10, marginTop: 4 }}>
                        Варианты: {p.name_variants.join(", ")}
                      </div>
                    )}
                  </div>
                  <button onClick={() => startEdit(p)} style={{
                    background: "transparent", border: "none", cursor: "pointer", padding: 4,
                  }} title="Редактировать">
                    <Icon d={Icons.pencil} size={16} color={T.dim} />
                  </button>
                  <button onClick={() => handleDelete(p.id, p.canonical_name)} style={{
                    background: "transparent", border: "none", cursor: "pointer", padding: 4,
                  }} title="Удалить из словаря">
                    <Icon d={Icons.trash} size={16} color={T.red + "aa"} />
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

function MyOrdersPage() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api("/orders").then((data) => {
      setOrders(Array.isArray(data) ? data : data?.items || []);
      setLoading(false);
    });
  }, []);

  if (loading) return <Loading />;

  return (
    <div style={{ padding: 16 }}>
      <h2 style={{ margin: "0 0 16px", color: T.gold, fontSize: 20, fontFamily: "'Cormorant Garamond', serif" }}>
        Мои заказы
      </h2>
      {orders.length === 0 ? (
        <Empty msg="" />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {orders.map((order) => (
            <div
              key={order.id}
              style={{
                padding: "12px 14px", background: T.card, borderRadius: 8,
                borderLeft: `3px solid ${T.gold}`,
              }}
            >
              <div style={{ color: T.text, fontSize: 14, fontFamily: "'Cormorant Garamond', serif" }}>
                Записка #{order.id}
              </div>
              <div style={{ color: T.dim, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", marginTop: 4 }}>
                {order.ordered_at ? order.ordered_at.slice(0, 10) : order.created_at?.slice(0, 10) || "—"}
                {order.source_channel ? ` · ${order.source_channel}` : ""}
              </div>
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
          { id: "persons", label: "Словарь имён" },
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
      {section === "persons" && <PersonManager />}
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

const TABS_FULL = [
  { id: "today", label: "Сегодня", icon: Icons.calendar },
  { id: "search", label: "Поиск", icon: Icons.search },
  { id: "add", label: "Записка", icon: Icons.plus },
  { id: "upload", label: "CSV", icon: Icons.upload },
  { id: "stats", label: "Стат.", icon: Icons.bar },
  { id: "db", label: "БД", icon: Icons.db },
];

const TABS_USER = [
  { id: "add", label: "Записка", icon: Icons.plus },
  { id: "myOrders", label: "Мои заказы", icon: Icons.list },
];

export default function SinodikApp() {
  const [tab, setTab] = useState("today");
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [loginOpen, setLoginOpen] = useState(false);
  const [loginStep, setLoginStep] = useState("email");
  const [loginEmail, setLoginEmail] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginOtpCode, setLoginOtpCode] = useState("");
  const [loginSubmitting, setLoginSubmitting] = useState(false);
  authRef.current = { token, setToken, setUser };

  const openLogin = () => {
    setLoginOpen(true);
    setLoginStep("email");
    setLoginEmail("");
    setLoginError("");
    setLoginOtpCode("");
  };

  const closeLogin = () => {
    setLoginOpen(false);
    setLoginStep("email");
    setLoginEmail("");
    setLoginError("");
    setLoginOtpCode("");
  };

  const handleRequestOtp = async () => {
    const email = loginEmail.trim();
    if (!email) return;
    setLoginSubmitting(true);
    setLoginError("");
    try {
      const res = await fetch(`${API}/auth/request-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (res.status === 429) {
        setLoginError("Слишком много запросов");
        return;
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setLoginError(body.detail || "Ошибка");
        return;
      }
      if (res.status === 202) {
        setLoginStep("otp");
        setLoginError("");
      }
    } finally {
      setLoginSubmitting(false);
    }
  };

  const handleVerifyOtp = async () => {
    const email = loginEmail.trim();
    const code = loginOtpCode.trim();
    if (!email || !code) return;
    setLoginSubmitting(true);
    setLoginError("");
    try {
      const res = await fetch(`${API}/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code }),
      });
      if (res.status === 401) {
        setLoginError("Неверный или истёкший код");
        return;
      }
      if (!res.ok) {
        setLoginError("Ошибка");
        return;
      }
      const data = await res.json();
      const newToken = data.token;
      const userData = data.user;
      if (newToken && userData) {
        localStorage.setItem(AUTH_KEY, newToken);
        setToken(newToken);
        setUser(userData);
        closeLogin();
      }
    } finally {
      setLoginSubmitting(false);
    }
  };

  const logout = () => {
    localStorage.removeItem(AUTH_KEY);
    setToken(null);
    setUser(null);
  };

  const visibleTabs = !user ? null : user.role === "admin" ? TABS_FULL : TABS_USER;

  // When non-admin, ensure tab is add or myOrders
  useEffect(() => {
    if (user && user.role !== "admin" && visibleTabs && !visibleTabs.some((t) => t.id === tab)) {
      setTab("add");
    }
  }, [user, tab, visibleTabs]);

  // Hydrate user from localStorage token on mount
  useEffect(() => {
    const stored = localStorage.getItem(AUTH_KEY);
    if (!stored) {
      setUser(null);
      return;
    }
    fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${stored}` } })
      .then((res) => {
        if (res.status === 401) {
          localStorage.removeItem(AUTH_KEY);
          setToken(null);
          setUser(null);
          return;
        }
        if (res.ok) {
          return res.json().then((data) => {
            setToken(stored);
            setUser(data);
          });
        }
      })
      .catch(() => setUser(null));
  }, []);

  return (
    <div style={{
      background: T.bg, color: T.text, minHeight: "100vh",
      fontFamily: "'Cormorant Garamond', serif",
      display: "flex", flexDirection: "column",
      maxWidth: 480, margin: "0 auto",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet" />

      {/* Login modal: one popup, email → OTP, errors at top, no code-sent hint, no Back on OTP */}
      {loginOpen && (
        <div
          style={{
            position: "fixed", inset: 0, zIndex: 1000,
            background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center",
            padding: 16,
          }}
          onClick={(e) => e.target === e.currentTarget && closeLogin()}
        >
          <div
            style={{
              background: T.card, borderRadius: 12, border: `1px solid ${T.border}`,
              padding: 24, width: "100%", maxWidth: 360,
              boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
              <span style={{ color: T.gold, fontSize: 18, fontWeight: 700, fontFamily: "'Cormorant Garamond', serif" }}>
                Вход
              </span>
              <button onClick={closeLogin} style={{ background: "transparent", border: "none", cursor: "pointer", padding: 4 }}>
                <Icon d={Icons.x} size={20} color={T.dim} />
              </button>
            </div>
            {loginError && (
              <div style={{
                marginBottom: 12, padding: 10, borderRadius: 8,
                background: T.red + "15", border: `1px solid ${T.red}44`,
                color: T.red, fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
              }}>
                {loginError}
              </div>
            )}
            {loginStep === "email" ? (
              <>
                <label style={LabelStyle()}>Email</label>
                <input
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder="example@mail.ru"
                  style={{ ...InputStyle(), marginBottom: 16 }}
                  onKeyDown={(e) => e.key === "Enter" && handleRequestOtp()}
                />
                <button
                  onClick={handleRequestOtp}
                  disabled={loginSubmitting || !loginEmail.trim()}
                  style={{
                    width: "100%", padding: 12, borderRadius: 8, border: "none",
                    background: T.gold, color: T.bg, fontSize: 14, fontWeight: 600,
                    cursor: loginSubmitting ? "wait" : "pointer", fontFamily: "'JetBrains Mono', monospace",
                    opacity: loginSubmitting || !loginEmail.trim() ? 0.6 : 1,
                  }}
                >
                  {loginSubmitting ? "Отправка..." : "Получить код"}
                </button>
              </>
            ) : (
              <>
                <label style={LabelStyle()}>Код из письма</label>
                <input
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  value={loginOtpCode}
                  onChange={(e) => setLoginOtpCode(e.target.value)}
                  placeholder="Введите код"
                  style={{ ...InputStyle(), marginBottom: 16 }}
                  onKeyDown={(e) => e.key === "Enter" && handleVerifyOtp()}
                />
                <button
                  onClick={handleVerifyOtp}
                  disabled={loginSubmitting || !loginOtpCode.trim()}
                  style={{
                    width: "100%", padding: 12, borderRadius: 8, border: "none",
                    background: T.gold, color: T.bg, fontSize: 14, fontWeight: 600,
                    cursor: loginSubmitting ? "wait" : "pointer", fontFamily: "'JetBrains Mono', monospace",
                    opacity: loginSubmitting || !loginOtpCode.trim() ? 0.6 : 1,
                  }}
                >
                  {loginSubmitting ? "Проверка..." : "Войти"}
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Header */}
      <div style={{
        padding: "14px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10,
        background: T.surface, borderBottom: `1px solid ${T.border}`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
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
        {!user ? (
          <button
            onClick={openLogin}
            style={{
              padding: "8px 14px", borderRadius: 8, border: `1px solid ${T.gold}44`,
              background: T.gold + "22", color: T.gold, cursor: "pointer",
              fontSize: 12, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            Войти
          </button>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {user.role !== "admin" && (
              <button
                onClick={() => setTab("myOrders")}
                style={{
                  padding: "8px 12px", borderRadius: 8, border: "none",
                  background: "transparent", color: T.gold, cursor: "pointer",
                  fontSize: 12, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace",
                }}
              >
                Мои заказы
              </button>
            )}
            <button
              onClick={logout}
              style={{
                padding: "8px 14px", borderRadius: 8, border: `1px solid ${T.border}`,
                background: "transparent", color: T.dim, cursor: "pointer",
                fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              Выйти
            </button>
          </div>
        )}
      </div>

      {/* Content: guest = form only; user = tabs; admin = full tabs */}
      <div style={{ flex: 1, overflowY: "auto", paddingBottom: visibleTabs ? 70 : 16 }}>
        {!user ? (
          <AddPage />
        ) : user.role === "admin" ? (
          <>
            {tab === "today" && <TodayPage />}
            {tab === "search" && <SearchPage />}
            {tab === "add" && <AddPage />}
            {tab === "upload" && <UploadPage />}
            {tab === "stats" && <StatsPage />}
            {tab === "db" && <DbManagePage />}
          </>
        ) : (
          <>
            {tab === "add" && <AddPage />}
            {tab === "myOrders" && <MyOrdersPage />}
          </>
        )}
      </div>

      {/* Bottom Tab Bar: only when authenticated */}
      {visibleTabs && (
        <div style={{
          position: "fixed", bottom: 0, left: "50%", transform: "translateX(-50%)",
          width: "100%", maxWidth: 480,
          display: "flex", background: T.surface,
          borderTop: `1px solid ${T.border}`,
          paddingBottom: "env(safe-area-inset-bottom, 8px)",
        }}>
          {visibleTabs.map((t) => (
            <Tab key={t.id} active={tab === t.id} label={t.label} icon={t.icon} onClick={() => setTab(t.id)} />
          ))}
        </div>
      )}
    </div>
  );
}
