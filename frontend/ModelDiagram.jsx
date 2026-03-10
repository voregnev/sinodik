import { useState } from "react";

const C = {
  bg: "#0a0e1a", surface: "#131825", card: "#1a2035", border: "#2a3555",
  gold: "#c9a84c", text: "#e8dcc8", dim: "#6b7a99",
  green: "#4ade80", red: "#f87171", blue: "#60a5fa", purple: "#a78bfa",
  cyan: "#22d3ee", orange: "#fb923c", pink: "#f472b6",
};

const mono = "'JetBrains Mono', monospace";
const serif = "'Cormorant Garamond', serif";

const Badge = ({ children, color }) => (
  <span style={{
    display: "inline-block", background: color + "22", color,
    border: `1px solid ${color}44`, borderRadius: 4,
    padding: "1px 6px", fontSize: 10, fontWeight: 600, fontFamily: mono,
  }}>{children}</span>
);

// ─── ERD Box ──────────────────────────────────────────────
function TableBox({ name, emoji, color, fields, badge, highlight = false }) {
  return (
    <div style={{
      background: highlight ? color + "08" : C.card,
      border: `1.5px solid ${color}${highlight ? "88" : "44"}`,
      borderRadius: 10, padding: 14, position: "relative",
      boxShadow: highlight ? `0 0 30px ${color}15` : "none",
    }}>
      {badge && (
        <div style={{
          position: "absolute", top: -10, right: 12,
          background: color, color: C.bg, fontSize: 9, fontWeight: 800,
          padding: "2px 8px", borderRadius: 4, fontFamily: mono, letterSpacing: 0.5,
        }}>{badge}</div>
      )}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <span style={{ fontSize: 20 }}>{emoji}</span>
        <span style={{ color, fontSize: 14, fontWeight: 700, fontFamily: mono }}>{name}</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
        {fields.map((f, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 8, padding: "3px 0",
            borderBottom: i < fields.length - 1 ? `1px solid ${C.border}` : "none",
          }}>
            {f.pk && <span style={{ color: C.gold, fontSize: 9, fontFamily: mono, fontWeight: 800 }}>PK</span>}
            {f.fk && <span style={{ color: C.purple, fontSize: 9, fontFamily: mono, fontWeight: 800 }}>FK</span>}
            {!f.pk && !f.fk && <span style={{ width: 16 }} />}
            <span style={{
              color: f.highlight ? color : C.text, fontSize: 12, fontWeight: f.highlight ? 700 : 400,
              fontFamily: mono, flex: 1,
            }}>{f.name}</span>
            <span style={{ color: C.dim, fontSize: 10, fontFamily: mono }}>{f.type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Arrow connector ──────────────────────────────────────
function Connector({ label, sublabel, color = C.dim }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: "4px 0" }}>
      <div style={{
        width: 2, height: 20, background: color + "66", margin: "0 auto",
      }} />
      <div style={{
        position: "absolute", background: C.surface, padding: "0 6px",
        color, fontSize: 10, fontFamily: mono, fontWeight: 600,
      }}>
        {label}
        {sublabel && <span style={{ color: C.dim, fontWeight: 400 }}> {sublabel}</span>}
      </div>
    </div>
  );
}

// ─── Flow Example ─────────────────────────────────────────
function FlowExample() {
  const steps = [
    { label: "CSV строка / форма", color: C.cyan, content: '"Ангелины Анны отр.Тимофея" / Сорокоуст / О здравии · user_email при «Известить о принятии»' },
    { label: "Order", color: C.blue, content: 'user_email · need_receipt · source: csv|form · external_id' },
    { label: "Name Parser", color: C.purple, content: '→ Ангелина, Анна, Тимофей [отрок] + suffix «со чадом»' },
    { label: "3× Commemoration", color: C.orange, content: '' },
  ];

  const comms = [
    { name: "Ангелина", prefix: null, suffix: null, type: "здравие", period: "сорокоуст", expires: "2026-04-05" },
    { name: "Анна", prefix: null, suffix: null, type: "здравие", period: "сорокоуст", expires: "2026-04-05" },
    { name: "Тимофей", prefix: "отр.", suffix: "со чадом", type: "здравие", period: "сорокоуст", expires: "2026-04-05" },
  ];

  return (
    <div style={{ padding: 16 }}>
      {steps.map((s, i) => (
        <div key={i}>
          {i > 0 && (
            <div style={{ display: "flex", justifyContent: "center", padding: "4px 0" }}>
              <span style={{ color: C.dim, fontSize: 16 }}>↓</span>
            </div>
          )}
          <div style={{
            background: s.color + "11", border: `1px solid ${s.color}44`,
            borderRadius: 8, padding: "8px 12px", borderLeft: `3px solid ${s.color}`,
          }}>
            <div style={{ color: s.color, fontSize: 11, fontWeight: 700, fontFamily: mono }}>{s.label}</div>
            {s.content && <div style={{ color: C.dim, fontSize: 11, fontFamily: mono, marginTop: 2 }}>{s.content}</div>}
          </div>
        </div>
      ))}

      {/* Individual commemoration records */}
      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4, paddingLeft: 12 }}>
        {comms.map((c, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 8,
            background: C.card, borderRadius: 6, padding: "6px 10px",
            borderLeft: `3px solid ${C.green}`,
          }}>
            <span style={{ color: C.text, fontSize: 13, fontFamily: serif, fontWeight: 700, minWidth: 80 }}>
              {c.prefix && <span style={{ color: C.dim, fontSize: 10, fontStyle: "italic" }}>{c.prefix} </span>}
              {c.name}
              {c.suffix && <span style={{ color: C.dim, fontSize: 10, fontStyle: "italic" }}> {c.suffix}</span>}
            </span>
            <Badge color={C.green}>{c.type}</Badge>
            <Badge color={C.gold}>{c.period}</Badge>
            <span style={{ color: C.dim, fontSize: 10, fontFamily: mono, marginLeft: "auto" }}>→ {c.expires}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Dates Explanation ────────────────────────────────────
function DatesExplain() {
  const dates = [
    { name: "ordered_at", label: "Дата заказа", desc: "Когда заказ оформлен (из CSV/формы)", color: C.blue, example: "2026-02-24 11:56" },
    { name: "starts_at", label: "Начало чтения", desc: "Когда начинается поминовение (может быть позже заказа)", color: C.green, example: "2026-02-24 11:56" },
    { name: "expires_at", label: "Дата окончания", desc: "calculate_expires_at(starts_at, period_type)", color: C.red, example: "2026-04-05 11:56" },
  ];

  return (
    <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
      {/* Timeline visual */}
      <div style={{
        background: C.card, borderRadius: 10, padding: 16,
        border: `1px solid ${C.border}`,
      }}>
        <div style={{ color: C.text, fontSize: 13, fontFamily: serif, fontWeight: 700, marginBottom: 12 }}>
          Timeline: Сорокоуст (40 дней)
        </div>
        <div style={{ position: "relative", height: 50, margin: "0 10px" }}>
          {/* Line */}
          <div style={{ position: "absolute", top: 20, left: 0, right: 0, height: 2, background: C.border }} />
          <div style={{ position: "absolute", top: 20, left: 0, right: "30%", height: 2, background: C.green + "88" }} />

          {/* Dots */}
          {[
            { left: "0%", color: C.blue, label: "ordered_at", sub: "24.02" },
            { left: "5%", color: C.green, label: "starts_at", sub: "24.02" },
            { left: "70%", color: C.red, label: "expires_at", sub: "05.04" },
          ].map((d, i) => (
            <div key={i} style={{ position: "absolute", left: d.left, top: 12 }}>
              <div style={{ width: 16, height: 16, borderRadius: "50%", background: d.color, border: `2px solid ${C.bg}` }} />
              <div style={{ color: d.color, fontSize: 9, fontFamily: mono, fontWeight: 700, marginTop: 4, whiteSpace: "nowrap", transform: "translateX(-30%)" }}>
                {d.label}
              </div>
              <div style={{ color: C.dim, fontSize: 9, fontFamily: mono, transform: "translateX(-20%)" }}>{d.sub}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Dates cards */}
      {dates.map((d, i) => (
        <div key={i} style={{
          background: C.card, borderRadius: 8, padding: "10px 14px",
          borderLeft: `3px solid ${d.color}`,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <span style={{ color: d.color, fontFamily: mono, fontSize: 12, fontWeight: 700 }}>{d.name}</span>
              <span style={{ color: C.dim, fontSize: 11, marginLeft: 8 }}>{d.label}</span>
            </div>
            <span style={{ color: C.dim, fontFamily: mono, fontSize: 10 }}>{d.example}</span>
          </div>
          <div style={{ color: C.dim, fontSize: 11, marginTop: 4 }}>{d.desc}</div>
        </div>
      ))}

      {/* expires_at function */}
      <div style={{
        background: C.surface, borderRadius: 8, padding: 14,
        border: `1px solid ${C.gold}44`, fontFamily: mono, fontSize: 11,
      }}>
        <div style={{ color: C.gold, fontWeight: 700, marginBottom: 8 }}>calculate_expires_at(starts_at, period_type)</div>
        <div style={{ color: C.dim, lineHeight: 1.8 }}>
          <span style={{ color: C.text }}>разовое</span>   → starts_at + <span style={{ color: C.green }}>1</span> день<br />
          <span style={{ color: C.text }}>сорокоуст</span> → starts_at + <span style={{ color: C.green }}>40</span> дней<br />
          <span style={{ color: C.text }}>полгода</span>   → starts_at + <span style={{ color: C.green }}>182</span> дня<br />
          <span style={{ color: C.text }}>год</span>       → starts_at + <span style={{ color: C.green }}>365</span> дней<br />
        </div>
      </div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────
const tabs = [
  { id: "erd", label: "Модель" },
  { id: "flow", label: "Flow" },
  { id: "dates", label: "Даты" },
  { id: "api", label: "API" },
];

export default function ModelDiagram() {
  const [tab, setTab] = useState("erd");

  return (
    <div style={{ background: C.bg, color: C.text, minHeight: "100vh", fontFamily: serif }}>
      <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{
        padding: "16px 16px 12px", background: C.surface,
        borderBottom: `1px solid ${C.border}`,
        display: "flex", alignItems: "center", gap: 10,
      }}>
        <span style={{ fontSize: 24 }}>☦️</span>
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: C.gold, letterSpacing: 2 }}>СИНОДИК</div>
          <div style={{ fontSize: 9, color: C.dim, fontFamily: mono }}>DATA MODEL v2 — COMMEMORATION = ATOMIC UNIT</div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", background: C.surface, borderBottom: `1px solid ${C.border}` }}>
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            flex: 1, padding: "10px 0", background: tab === t.id ? C.card : "transparent",
            color: tab === t.id ? C.gold : C.dim, border: "none", cursor: "pointer",
            borderBottom: tab === t.id ? `2px solid ${C.gold}` : "2px solid transparent",
            fontSize: 12, fontWeight: 600, fontFamily: mono,
          }}>{t.label}</button>
        ))}
      </div>

      {/* Content */}
      <div style={{ padding: "16px 14px", maxWidth: 520, margin: "0 auto" }}>

        {tab === "erd" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Key insight box */}
            <div style={{
              background: C.gold + "11", border: `1px solid ${C.gold}44`,
              borderRadius: 10, padding: 14,
            }}>
              <div style={{ color: C.gold, fontWeight: 700, fontSize: 13, fontFamily: mono, marginBottom: 6 }}>
                KEY: одна запись = одно имя
              </div>
              <div style={{ color: C.dim, fontSize: 12, lineHeight: 1.6 }}>
                <b style={{ color: C.text }}>Commemoration</b> — атомарная единица.
                Одна строка в таблице = одно конкретное имя с полным набором дат и типом.
                Если в заказе 5 имён → 5 записей Commemoration.
              </div>
            </div>

            {/* Person */}
            <TableBox
              name="persons"
              emoji="👤"
              color={C.purple}
              badge="СПРАВОЧНИК"
              fields={[
                { name: "id", type: "serial", pk: true },
                { name: "canonical_name", type: "varchar(100) UNIQUE", highlight: true },
                { name: "genitive_name", type: "varchar(100)" },
                { name: "gender", type: "м | ж" },
                { name: "name_variants", type: "text[]" },
                { name: "embedding", type: "vector(384)" },
                { name: "created_at", type: "timestamptz" },
              ]}
            />

            <div style={{ textAlign: "center", color: C.dim, fontSize: 13 }}>
              ↑ <span style={{ fontFamily: mono, fontSize: 10 }}>person_id (M:1)</span>
            </div>

            {/* Commemoration */}
            <TableBox
              name="commemorations"
              emoji="📿"
              color={C.orange}
              badge="ATOMIC UNIT"
              highlight={true}
              fields={[
                { name: "id", type: "serial", pk: true },
                { name: "person_id", type: "→ persons.id", fk: true, highlight: true },
                { name: "order_id", type: "→ orders.id", fk: true },
                { name: "order_type", type: "здравие | упокоение", highlight: true },
                { name: "period_type", type: "разовое | сорокоуст | полгода | год", highlight: true },
                { name: "prefix", type: "в., нпр., мл., иер. уб." },
                { name: "suffix", type: "со чадом | со чады" },
                { name: "ordered_at", type: "timestamptz", highlight: true },
                { name: "starts_at", type: "timestamptz", highlight: true },
                { name: "expires_at", type: "timestamptz", highlight: true },
                { name: "position", type: "integer" },
                { name: "is_active", type: "boolean" },
                { name: "created_at", type: "timestamptz" },
              ]}
            />

            <div style={{ textAlign: "center", color: C.dim, fontSize: 13 }}>
              ↓ <span style={{ fontFamily: mono, fontSize: 10 }}>order_id (M:1)</span>
            </div>

            {/* Order */}
            <TableBox
              name="orders"
              emoji="📋"
              color={C.blue}
              badge="METADATA"
              fields={[
                { name: "id", type: "serial", pk: true },
                { name: "user_email", type: "varchar(255)", highlight: true },
                { name: "need_receipt", type: "boolean" },
                { name: "source_channel", type: "csv | form | api" },
                { name: "source_raw", type: "text" },
                { name: "external_id", type: "varchar(100) UNIQUE" },
                { name: "ordered_at", type: "timestamptz" },
                { name: "created_at", type: "timestamptz" },
              ]}
            />

            {/* Relationship summary */}
            <div style={{
              background: C.surface, borderRadius: 8, padding: 12,
              border: `1px solid ${C.border}`, fontFamily: mono, fontSize: 11,
              color: C.dim, lineHeight: 1.8,
            }}>
              <div style={{ color: C.text, fontWeight: 700, marginBottom: 4 }}>Связи:</div>
              <span style={{ color: C.purple }}>Person</span> (1) ← (M) <span style={{ color: C.orange }}>Commemoration</span> (M) → (1) <span style={{ color: C.blue }}>Order</span><br />
              <br />
              <span style={{ color: C.dim }}>1 заказ с 5 именами → 1 Order + 5 Commemorations</span><br />
              <span style={{ color: C.dim }}>1 имя в 3 заказах → 1 Person + 3 Commemorations</span>
            </div>
          </div>
        )}

        {tab === "flow" && <FlowExample />}

        {tab === "dates" && <DatesExplain />}

        {tab === "api" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              { method: "POST", path: "/api/v1/upload/csv", desc: "Загрузка CSV → N commemorations. Query: delimiter, starts_at", color: C.green },
              { method: "POST", path: "/api/v1/orders", desc: "Ручная записка. Body: order_type, period_type, names_text, user_email (при «Известить о принятии»), need_receipt, starts_at", color: C.green },
              { method: "GET", path: "/api/v1/orders", desc: "Список заказов (limit, offset)", color: C.blue },
              { method: "PATCH", path: "/api/v1/orders/{id}", desc: "Редактирование заказа (user_email, ordered_at, need_receipt)", color: C.blue },
              { method: "DELETE", path: "/api/v1/orders/{id}", desc: "Удаление заказа", color: C.red },
              { method: "GET", path: "/api/v1/commemorations", desc: "Список поминовений для управления. Query: no_start_date, limit, offset", color: C.blue },
              { method: "PATCH", path: "/api/v1/commemorations/{id}", desc: "Редактирование записи: prefix, suffix, order_type, period_type, starts_at (expires_at пересчитывается)", color: C.orange },
              { method: "DELETE", path: "/api/v1/commemorations/{id}", desc: "Удаление одной записи (одно имя)", color: C.red },
              { method: "POST", path: "/api/v1/commemorations/bulk-update", desc: "Массовая установка starts_at для списка id (expires_at пересчитывается)", color: C.orange },
              { method: "GET", path: "/api/v1/names/today", desc: "Активные commemorations на сегодня. Query: order_type", color: C.blue },
              { method: "GET", path: "/api/v1/names/search?q=...", desc: "Fuzzy-поиск по Person (trigram + vector)", color: C.blue },
              { method: "GET", path: "/api/v1/names/stats", desc: "Статистика: total, active, by_type, by_period", color: C.blue },
              { method: "GET", path: "/api/v1/names/by-user?email=...", desc: "Поминовения заказчика по email", color: C.blue },
            ].map((e, i) => (
              <div key={i} style={{
                background: C.card, borderRadius: 8, padding: "10px 12px",
                borderLeft: `3px solid ${e.color}`,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Badge color={e.color}>{e.method}</Badge>
                  <span style={{ color: C.text, fontFamily: mono, fontSize: 11 }}>{e.path}</span>
                </div>
                <div style={{ color: C.dim, fontSize: 11, marginTop: 4 }}>{e.desc}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
