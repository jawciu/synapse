import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type PatternEntry = {
  name: string;
  category: string;
  description?: string;
  occurrences: number;
};

type ThemeEntry = {
  name: string;
  description: string;
};

type IFSPart = {
  name: string;
  role: string;
  description: string;
  occurrences: number;
};

type SchemaEntry = {
  name: string;
  domain: string;
  coping_style: string;
  description: string;
  occurrences: number;
};

type EmotionEntry = {
  name: string;
  valence: string;
  intensity: number;
};

type PersonEntry = {
  name: string;
  relationship: string;
  description: string;
  occurrences: number;
};

type BodySignal = {
  name: string;
  location: string;
  occurrences: number;
};

type Extraction = {
  patterns: Array<{ name: string; category: string; strength: number }>;
  emotions: Array<{ name: string; valence: string; intensity: number }>;
  themes: ThemeEntry[];
  ifs_parts: IFSPart[];
  schemas: SchemaEntry[];
  people: PersonEntry[];
  body_signals: BodySignal[];
};

type Summary = {
  total_reflections: number;
  total_patterns: number;
  total_emotions: number;
  total_themes: number;
  total_people: number;
  total_body_signals: number;
};

type DashboardPayload = {
  patterns_by_category: Record<string, PatternEntry[]>;
  ifs_parts: IFSPart[];
  schemas: SchemaEntry[];
  emotions: EmotionEntry[];
  people: PersonEntry[];
  body_signals: BodySignal[];
  summary: Summary;
};

type ReflectionPayload = {
  extracted: Extraction;
  insights: string;
  follow_up_questions: string[];
};

type ReflectionResponse = {
  thread_id: string;
  result: ReflectionPayload;
};

type ChatMessage = {
  role: "user" | "assistant" | "ai";
  content: string;
};

type ChatResponse = {
  thread_id: string;
  answer: string;
  messages: Array<{ role?: string; content: string }>;
};

type View = "reflect" | "patterns" | "ask";

const API_URL = (import.meta as ImportMeta).env?.VITE_API_URL ?? "http://localhost:8000";
const categories = ["cognitive", "emotional", "relational", "behavioral"] as const;

const THEME_COLORS = {
  primary: "#8ab4f8",
  accent: "#bfa5ff",
  muted: "#928b8d",
  mutedBorder: "rgba(120, 110, 100, 0.24)",
  positive: "#9dc89a",
  negative: "#f2a6a6",
  neutral: "#f4c99f",
  bg1: "#f6f2e8",
  bg2: "#f0eadc",
};

const CATEGORY_PALETTE: Record<string, string> = {
  cognitive: "#f2a3bb",
  emotional: "#9dc7ec",
  relational: "#c8b4f2",
  behavioral: "#9ed4aa",
};

const CHART_TOOLTIP_STYLE = {
  contentStyle: {
    background: "rgba(255, 252, 246, 0.96)",
    borderColor: "#e4d9c6",
    color: "#3f3a34",
  },
  labelStyle: { color: "#3f3a34" },
  itemStyle: { color: "#3f3a34" },
};

const IF_ROLE_LABELS: Record<string, string> = {
  exile: "exile",
  manager: "protector",
  firefighter: "reactor",
};

const SCHEMA_DOMAIN_LABELS: Record<string, string> = {
  disconnection: "disconnection",
  impaired_autonomy: "impaired autonomy",
  impaired_limits: "impaired limits",
  other_directedness: "other-directedness",
  overvigilance: "overvigilance",
};

const COPING_LABELS: Record<string, string> = {
  surrender: "surrenders",
  avoidance: "avoids",
  overcompensation: "overcompensates",
  none: "none",
};

const EMPTY_EXTRACTION: Extraction = {
  patterns: [],
  emotions: [],
  themes: [],
  ifs_parts: [],
  schemas: [],
  people: [],
  body_signals: [],
};

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, Number((value * 100).toFixed(0))));
}

function capitalizeWord(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function roleName(value: string): string {
  return IF_ROLE_LABELS[value] ?? value;
}

function chartPct(values: EmotionEntry[]): { negative: number; neutral: number; positive: number } {
  if (!values.length) {
    return { negative: 0, neutral: 0, positive: 0 };
  }

  return values.reduce(
    (acc, item) => {
      const bucket = item.valence.toLowerCase();
      if (bucket === "negative") {
        acc.negative += item.intensity;
      } else if (bucket === "positive") {
        acc.positive += item.intensity;
      } else {
        acc.neutral += item.intensity;
      }
      return acc;
    },
    { negative: 0, neutral: 0, positive: 0 },
  );
}

function safeSlice<T>(items: T[], size = 0): T[] {
  return size > 0 ? items.slice(0, size) : items;
}

function App() {
  const [activeTab, setActiveTab] = useState<View>("reflect");
  const [dailyPrompt, setDailyPrompt] = useState("");
  const [reflectionText, setReflectionText] = useState("");
  const [reflectionBusy, setReflectionBusy] = useState(false);
  const [reflectionError, setReflectionError] = useState("");
  const [lastReflection, setLastReflection] = useState<ReflectionPayload | null>(null);

  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null);
  const [dashboardBusy, setDashboardBusy] = useState(false);

  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatThread, setChatThread] = useState<string | null>(null);

  useEffect(() => {
    const initialize = async () => {
      await fetchPrompt();
      await fetchDashboard();
    };

    initialize();
  }, []);

  const fetchPrompt = async () => {
    try {
      const promptResp = await fetch(`${API_URL}/api/daily-prompt`);
      const promptJson = (await promptResp.json()) as { prompt?: string };
      setDailyPrompt(promptJson.prompt || "");
    } catch {
      setDailyPrompt("What felt most alive in your body today?");
    }
  };

  const fetchDashboard = async () => {
    setDashboardBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/dashboard?limit=8`);
      const payload = (await res.json()) as DashboardPayload;
      setDashboard(payload);
    } catch {
      setDashboard({
        patterns_by_category: { cognitive: [], emotional: [], relational: [], behavioral: [] },
        ifs_parts: [],
        schemas: [],
        emotions: [],
        people: [],
        body_signals: [],
        summary: {
          total_reflections: 0,
          total_patterns: 0,
          total_emotions: 0,
          total_themes: 0,
          total_people: 0,
          total_body_signals: 0,
        },
      });
    } finally {
      setDashboardBusy(false);
    }
  };

  const submitReflection = async () => {
    if (!reflectionText.trim()) {
      return;
    }

    setReflectionBusy(true);
    setReflectionError("");

    try {
      const response = await fetch(`${API_URL}/api/reflection`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          reflection_text: reflectionText,
          daily_prompt: dailyPrompt || null,
          thread_id: null,
        }),
      });

      const payload = (await response.json()) as ReflectionResponse & { detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail || "Unable to run reflection");
      }

      setLastReflection(payload.result);
      setReflectionText("");
      await fetchDashboard();
    } catch (error) {
      setReflectionError((error as Error).message || "Could not process reflection.");
    } finally {
      setReflectionBusy(false);
    }
  };

  const sendChat = async () => {
    if (!chatInput.trim()) {
      return;
    }

    const userMessage = {
      role: "user" as const,
      content: chatInput.trim(),
    };

    const nextMessages = [...chatMessages, userMessage];
    setChatMessages(nextMessages);
    setChatInput("");
    setChatBusy(true);

    try {
      const thread = chatThread ?? `chat-${Date.now()}`;
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: userMessage.content, thread_id: thread }),
      });

      const payload = (await response.json()) as ChatResponse & { detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail || "Could not get response");
      }

      const normalizedMessages: ChatMessage[] = payload.messages
        .map((message) => {
          const role = (message.role === "user" ? "user" : message.role === "assistant" ? "assistant" : "ai") as ChatMessage["role"];
          return {
            role,
            content: String(message.content || ""),
          };
        })
        .filter((message) => message.content.trim().length > 0);

      let assistantMessage: ChatMessage | null = null;
      for (let index = normalizedMessages.length - 1; index >= 0; index -= 1) {
        const candidate = normalizedMessages[index];
        if (candidate.role !== "user") {
          assistantMessage = candidate;
          break;
        }
      }

      setChatThread(payload.thread_id);
      if (assistantMessage && assistantMessage.content.trim().length > 0) {
        setChatMessages((previous) => [...previous, assistantMessage]);
      } else {
        setChatMessages((previous) => [
          ...previous,
          {
            role: "assistant",
            content: payload.answer || "No response returned.",
          },
        ]);
      }
    } catch (error) {
      setChatMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: (error as Error).message || "Something went wrong while chatting.",
        },
      ]);
    } finally {
      setChatBusy(false);
    }
  };

  const extraction = useMemo<Extraction>(() => {
    return lastReflection?.extracted ? { ...EMPTY_EXTRACTION, ...lastReflection.extracted } : EMPTY_EXTRACTION;
  }, [lastReflection]);

  const insights = useMemo(() => lastReflection?.insights ?? "", [lastReflection]);
  const followUps = useMemo(() => lastReflection?.follow_up_questions ?? [], [lastReflection]);

  const topPatterns = useMemo(() => {
    if (!dashboard) {
      return [] as Array<{ label: string; value: number; category: string }>;
    }

    return categories
      .flatMap((category) => safeSlice(dashboard.patterns_by_category[category] ?? [], 0).map((entry) => ({
        label: entry.name,
        value: entry.occurrences || 0,
        category,
      })))
      .sort((a, b) => b.value - a.value)
      .slice(0, 12);
  }, [dashboard]);

  const emotionBars = useMemo(() => {
    if (!dashboard) {
      return [];
    }

    return dashboard.emotions.slice(0, 12).map((entry) => ({
      ...entry,
      value: clampPercent(entry.intensity),
      color:
        entry.valence.toLowerCase() === "negative"
          ? THEME_COLORS.negative
          : entry.valence.toLowerCase() === "positive"
            ? THEME_COLORS.positive
            : THEME_COLORS.neutral,
    }));
  }, [dashboard]);

  const byCategory = useMemo(() => {
    if (!dashboard) {
      return {} as Record<string, PatternEntry[]>;
    }

    return categories.reduce(
      (acc, category) => {
        acc[category] = safeSlice(dashboard.patterns_by_category[category] ?? [], 6);
        return acc;
      },
      {} as Record<string, PatternEntry[]>,
    );
  }, [dashboard]);

  const valenceTotals = useMemo(() => chartPct(dashboard?.emotions || []), [dashboard]);

  const pieSegments = [
    { name: "negative", value: Number((valenceTotals.negative * 100).toFixed(1)) },
    { name: "neutral", value: Number((valenceTotals.neutral * 100).toFixed(1)) },
    { name: "positive", value: Number((valenceTotals.positive * 100).toFixed(1)) },
  ];

  const totals = useMemo(() => {
    const summary = dashboard?.summary;
    return {
      reflections: summary?.total_reflections ?? 0,
      patterns: summary?.total_patterns ?? 0,
      emotions: summary?.total_emotions ?? 0,
      themes: summary?.total_themes ?? 0,
      people: summary?.total_people ?? 0,
      bodySignals: summary?.total_body_signals ?? 0,
    };
  }, [dashboard]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <p className="logo">synapse</p>
        <p className="subhead">TypeScript dashboard over the same LangGraph pipeline.</p>

        <section className="card panel">
          <h2>Daily Prompt</h2>
          <p>{dailyPrompt || "Loading prompt..."}</p>
          <div className="row-actions">
            <button type="button" onClick={fetchPrompt}>
              new prompt
            </button>
            <button type="button" onClick={() => setReflectionText(dailyPrompt)}>
              use prompt
            </button>
          </div>
        </section>

        <section className="card panel">
          <h2>Session</h2>
          <p>Chat thread: {chatThread ? chatThread.slice(0, 18) : "new"}</p>
          <button type="button" onClick={() => setChatThread(null)}>
            new conversation
          </button>
        </section>

        <section className="card panel stat-grid">
          <h2>Totals</h2>
          <p>{totals.reflections} reflections</p>
          <p>{totals.patterns} patterns</p>
          <p>{totals.emotions} emotions</p>
          <p>{totals.themes} themes</p>
          <p>{totals.people} people</p>
          <p>{totals.bodySignals} body signals</p>
        </section>
      </aside>

      <main className="content">
        <nav className="tabs" role="tablist" aria-label="Primary tabs">
          <button
            type="button"
            className={activeTab === "reflect" ? "active" : ""}
            onClick={() => setActiveTab("reflect")}
          >
            Reflect
          </button>
          <button
            type="button"
            className={activeTab === "patterns" ? "active" : ""}
            onClick={() => setActiveTab("patterns")}
          >
            Patterns
          </button>
          <button
            type="button"
            className={activeTab === "ask" ? "active" : ""}
            onClick={() => setActiveTab("ask")}
          >
            Ask
          </button>
        </nav>

        {activeTab === "reflect" ? (
          <section className="card">
            <h2>Reflect</h2>
            <textarea
              rows={7}
              value={reflectionText}
              placeholder="Write your reflection..."
              onChange={(event) => setReflectionText(event.target.value)}
            />
            <div className="toolbar">
              <button type="button" onClick={submitReflection} disabled={reflectionBusy || !reflectionText.trim()}>
                {reflectionBusy ? "Analyzing..." : "Submit Reflection"}
              </button>
            </div>
            {reflectionError ? <p className="error">{reflectionError}</p> : null}

            {lastReflection ? (
              <>
                <div className="result-grid">
                  <section className="panel">
                    <h3>Patterns</h3>
                    {extraction.patterns.length > 0 ? (
                      extraction.patterns.map((pattern) => (
                        <p key={pattern.name}>
                          <strong>{pattern.name}</strong> <span className="meta">({pattern.category})</span> -{' '}
                          {clampPercent(pattern.strength)}%
                        </p>
                      ))
                    ) : (
                      <p className="muted">No patterns detected yet.</p>
                    )}
                  </section>

                  <section className="panel">
                    <h3>Emotions</h3>
                    {extraction.emotions.length > 0 ? (
                      extraction.emotions.map((emotion) => (
                        <p key={emotion.name}>
                          <strong>{emotion.name}</strong> <span className="meta">({emotion.valence})</span> -{' '}
                          {clampPercent(emotion.intensity)}%
                        </p>
                      ))
                    ) : (
                      <p className="muted">No emotions detected.</p>
                    )}
                  </section>

                  <section className="panel">
                    <h3>Themes</h3>
                    {extraction.themes.length > 0 ? (
                      extraction.themes.map((theme) => (
                        <p key={theme.name}>
                          <strong>{theme.name}</strong>
                          <span className="muted"> - {theme.description}</span>
                        </p>
                      ))
                    ) : (
                      <p className="muted">No themes surfaced.</p>
                    )}
                  </section>

                  <section className="panel">
                    <h3>IFS Parts</h3>
                    {extraction.ifs_parts.length > 0 ? (
                      extraction.ifs_parts.map((part) => (
                        <p key={part.name}>
                          <strong>{part.name}</strong> <span className="meta">({roleName(part.role)})</span>
                          <span className="muted"> - {part.description}</span>
                        </p>
                      ))
                    ) : (
                      <p className="muted">No IFS parts detected.</p>
                    )}
                  </section>

                  <section className="panel">
                    <h3>Schemas</h3>
                    {extraction.schemas.length > 0 ? (
                      extraction.schemas.map((schema) => (
                        <p key={schema.name}>
                          <strong>{schema.name}</strong>
                          <span className="meta">
                            ({SCHEMA_DOMAIN_LABELS[schema.domain] || schema.domain}, {COPING_LABELS[schema.coping_style] || schema.coping_style})
                          </span>
                          <span className="muted"> - {schema.description}</span>
                        </p>
                      ))
                    ) : (
                      <p className="muted">No schema patterns detected.</p>
                    )}
                  </section>

                  <section className="panel">
                    <h3>People</h3>
                    {extraction.people.length > 0 ? (
                      extraction.people.map((person) => (
                        <p key={person.name}>
                          <strong>{person.name}</strong>
                          <span className="meta"> ({person.relationship})</span>
                          {person.description ? <span className="muted"> - {person.description}</span> : null}
                        </p>
                      ))
                    ) : (
                      <p className="muted">No people detected.</p>
                    )}
                  </section>

                  <section className="panel">
                    <h3>Body Signals</h3>
                    {extraction.body_signals.length > 0 ? (
                      extraction.body_signals.map((signal) => (
                        <p key={signal.name}>
                          <strong>{signal.name}</strong>
                          <span className="meta"> ({signal.location})</span>
                        </p>
                      ))
                    ) : (
                      <p className="muted">No body signals detected.</p>
                    )}
                  </section>

                  <section className="panel wide-panel">
                    <h3>Insights</h3>
                    <p>{insights || "--"}</p>
                  </section>

                  <section className="panel wide-panel">
                    <h3>Follow-up Questions</h3>
                    {followUps.length > 0 ? (
                      <ul>
                        {followUps.map((followUp) => (
                          <li key={followUp}>{followUp}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="muted">No follow-ups yet.</p>
                    )}
                  </section>
                </div>
              </>
            ) : null}
          </section>
        ) : null}

        {activeTab === "patterns" ? (
          <section className="panel-grid">
            <section className="card span-two">
              <div className="panel-head">
                <h2>Top Patterns by Category</h2>
                <button type="button" onClick={fetchDashboard} disabled={dashboardBusy}>
                  {dashboardBusy ? "Refreshing..." : "Refresh"}
                </button>
              </div>

              <div className="category-grid">
                {categories.map((category) => {
                  const rows = byCategory[category] ?? [];
                  return (
                    <article className="panel compact" key={category}>
                      <h3>{capitalizeWord(category)}</h3>
                      {rows.length === 0 ? (
                        <p className="muted">None yet.</p>
                      ) : (
                        <ResponsiveContainer width="100%" height={170}>
                          <BarChart data={rows} layout="vertical">
                            <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                            <XAxis type="number" stroke={THEME_COLORS.muted} />
                            <YAxis dataKey="name" type="category" width={120} stroke={THEME_COLORS.muted} />
                            <Tooltip {...CHART_TOOLTIP_STYLE} />
                            <Bar dataKey="occurrences" radius={6} fill={CATEGORY_PALETTE[category]} />
                          </BarChart>
                        </ResponsiveContainer>
                      )}
                    </article>
                  );
                })}
              </div>
            </section>

            <section className="card">
              <h2>Pattern Mix</h2>
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={topPatterns} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                    <XAxis type="number" stroke={THEME_COLORS.muted} />
                    <YAxis dataKey="label" type="category" width={160} stroke={THEME_COLORS.muted} />
                    <Tooltip {...CHART_TOOLTIP_STYLE} />
                    <Bar dataKey="value" radius={6}>
                      {topPatterns.map((entry, index) => (
                        <Cell key={`${entry.label}-${index}`} fill={CATEGORY_PALETTE[entry.category] ?? THEME_COLORS.primary} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section className="card">
              <h2>Emotion Intensity</h2>
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={emotionBars}>
                    <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                    <XAxis dataKey="name" stroke={THEME_COLORS.muted} />
                    <YAxis stroke={THEME_COLORS.muted} />
                    <Tooltip {...CHART_TOOLTIP_STYLE} />
                    <Line type="monotone" dataKey="value" stroke={THEME_COLORS.primary} strokeWidth={3} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section className="card split">
              <div>
                <h2>Valence Mix</h2>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={pieSegments} dataKey="value" nameKey="name" innerRadius={58} outerRadius={90} label>
                      <Cell fill={THEME_COLORS.negative} />
                      <Cell fill={THEME_COLORS.neutral} />
                      <Cell fill={THEME_COLORS.positive} />
                    </Pie>
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div>
                <h2>IFS & Schemas</h2>
                <h4>IFS</h4>
                {safeSlice(dashboard?.ifs_parts ?? [], 8).map((part) => (
                  <p key={part.name}>
                    <strong>{part.name}</strong>
                    <span className="meta"> ({part.role})</span> - {part.occurrences}
                  </p>
                ))}

                <h4>Schema</h4>
                {safeSlice(dashboard?.schemas ?? [], 8).map((schema) => (
                  <p key={schema.name}>
                    <strong>{schema.name}</strong>
                    <span className="meta">
                      ({SCHEMA_DOMAIN_LABELS[schema.domain] || schema.domain}, {COPING_LABELS[schema.coping_style] || schema.coping_style})
                    </span>
                    - {schema.occurrences}
                  </p>
                ))}
              </div>
            </section>

            <section className="card">
              <h2>People & Body Signals</h2>
              <div className="split-list">
                <div>
                  <h3>People</h3>
                  {safeSlice(dashboard?.people ?? [], 8).map((person) => (
                    <p key={person.name}>
                      <strong>{person.name}</strong>
                      <span className="meta"> ({person.relationship})</span> - {person.occurrences}
                    </p>
                  ))}
                </div>
                <div>
                  <h3>Body</h3>
                  {safeSlice(dashboard?.body_signals ?? [], 8).map((signal) => (
                    <p key={signal.name}>
                      <strong>{signal.name}</strong>
                      <span className="meta"> ({signal.location})</span> - {signal.occurrences}
                    </p>
                  ))}
                </div>
              </div>
            </section>
          </section>
        ) : null}

        {activeTab === "ask" ? (
          <section className="card chat-card">
            <h2>Ask Your Graph</h2>
            <div className="chat-log">
              {chatMessages.map((message, index) => (
                <p key={`${message.role}-${index}`} className={`chat-line ${message.role}`}>
                  <strong>{message.role === "user" ? "You" : "synapse"}:</strong> {message.content}
                </p>
              ))}
              {chatBusy ? <p className="muted">Assistant is thinking...</p> : null}
            </div>
            <div className="chat-inputs">
              <input
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !chatBusy) {
                    sendChat();
                  }
                }}
                placeholder="Ask about patterns, people, or emotions..."
              />
              <button type="button" onClick={sendChat} disabled={chatBusy || !chatInput.trim()}>
                Send
              </button>
            </div>
          </section>
        ) : null}
      </main>
    </div>
  );
}

export { App };
