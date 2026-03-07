import { useEffect, useMemo, useState, type CSSProperties, type ComponentType, type SVGProps } from "react";
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
import {
  BodySignalIcon,
  EmotionIcon,
  FlowerIcon,
  JournalIcon,
  PatternIcon,
  PeopleIcon,
  RefreshIcon,
  ThemeIcon,
} from "./icons";

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

type TriggerPatternEntry = {
  name: string;
  category: string;
  links: number;
};

type PersonOverviewEntry = PersonEntry & {
  id: string;
  first_seen?: string | null;
  last_seen?: string | null;
  triggered_patterns: TriggerPatternEntry[];
};

type RelationshipMixEntry = {
  relationship: string;
  people_count: number;
  mentions: number;
};

type PeopleOverviewSummary = {
  total_people: number;
  total_mentions: number;
  unique_relationships: number;
  top_person: string | null;
  top_person_mentions: number;
  top_relationship: string | null;
  key_action: string;
};

type PeopleOverviewPayload = {
  people: PersonOverviewEntry[];
  relationship_mix: RelationshipMixEntry[];
  top_trigger_patterns: TriggerPatternEntry[];
  summary: PeopleOverviewSummary;
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

type ReflectionSource = {
  id: string;
  text: string;
  daily_prompt?: string | null;
  source?: string | null;
  created_at?: string | null;
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

type TotalSelection = "reflections" | "patterns" | "emotions" | "themes" | "people" | "bodySignals";
type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;

type View = "reflect" | "patterns" | "ask";

const API_URL = (import.meta as ImportMeta).env?.VITE_API_URL ?? "http://localhost:8000";
const categories = ["cognitive", "emotional", "relational", "behavioral"] as const;
const TOTAL_LABELS: Record<TotalSelection, string> = {
  reflections: "reflections",
  patterns: "patterns",
  emotions: "emotions",
  themes: "themes",
  people: "people",
  bodySignals: "body signals",
};

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

function formatSourceDate(value: string | null | undefined): string {
  if (!value) {
    return "Unknown date";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function titleCase(value: string): string {
  if (!value) {
    return value;
  }
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatReflectionSource(value: string | null | undefined): string {
  const source = (value || "").trim().toLowerCase();
  if (source === "telegram_text" || source === "telegram text" || source === "telegram") {
    return "telegram text";
  }
  if (source === "voice" || source === "telegram_voice" || source === "telegram voice" || source === "voice_note") {
    return "voice";
  }
  return "app";
}

function reflectionSourceKey(value: string | null | undefined): "app" | "telegram_text" | "voice" {
  const source = (value || "").trim().toLowerCase();
  if (source === "telegram_text" || source === "telegram text" || source === "telegram") {
    return "telegram_text";
  }
  if (source === "voice" || source === "telegram_voice" || source === "telegram voice" || source === "voice_note") {
    return "voice";
  }
  return "app";
}

function buildPromptDraft(prompt: string): string {
  const resolvedPrompt = prompt.trim() || "What felt most alive in your body today?";
  return [
    `Prompt: ${resolvedPrompt}`,
    "",
    "Short answer:",
    "[In 2-3 sentences, answer the prompt directly.]",
    "",
    "What happened (facts):",
    "[What happened, where, and with whom?]",
    "",
    "What I felt in my body:",
    "[Sensations: chest, stomach, shoulders, breath, etc.]",
    "",
    "What I felt emotionally:",
    "[Emotions + intensity, for example: anxious 7/10, relieved 4/10.]",
    "",
    "What pattern I noticed:",
    "[Any repeating thought, behavior, or reaction.]",
    "",
    "What I might try next:",
    "[One small action I can take today or tomorrow.]",
  ].join("\n");
}

function App() {
  const [activeTab, setActiveTab] = useState<View>("reflect");
  const [dailyPrompt, setDailyPrompt] = useState("");
  const [reflectionText, setReflectionText] = useState("");
  const [composerOpen, setComposerOpen] = useState(false);
  const [reflectionBusy, setReflectionBusy] = useState(false);
  const [reflectionError, setReflectionError] = useState("");
  const [lastReflection, setLastReflection] = useState<ReflectionPayload | null>(null);

  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null);
  const [dashboardBusy, setDashboardBusy] = useState(false);
  const [liveTime, setLiveTime] = useState(() => new Date());

  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatThread, setChatThread] = useState<string | null>(null);
  const [selectedTotal, setSelectedTotal] = useState<TotalSelection | null>(null);
  const [reflectionSources, setReflectionSources] = useState<ReflectionSource[]>([]);
  const [sourcesBusy, setSourcesBusy] = useState(false);
  const [sourcesError, setSourcesError] = useState("");
  const [peopleOverview, setPeopleOverview] = useState<PeopleOverviewPayload | null>(null);
  const [peopleBusy, setPeopleBusy] = useState(false);
  const [peopleError, setPeopleError] = useState("");
  const [reflectionsFilter, setReflectionsFilter] = useState<"all" | "app" | "telegram_text" | "voice">("all");
  const [reflectionsSort, setReflectionsSort] = useState<"newest" | "oldest">("newest");
  const [reflectionsQuery, setReflectionsQuery] = useState("");

  useEffect(() => {
    const initialize = async () => {
      await fetchPrompt();
      await fetchDashboard();
    };

    initialize();
  }, []);

  useEffect(() => {
    const tick = () => setLiveTime(new Date());
    tick();
    const intervalId = setInterval(tick, 1000);
    return () => {
      clearInterval(intervalId);
    };
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

  const fetchReflectionSources = async () => {
    setSourcesBusy(true);
    setSourcesError("");
    try {
      const response = await fetch(`${API_URL}/api/reflections`);
      const payload = (await response.json()) as ReflectionSource[] | { detail?: string };
      if (!response.ok) {
        const errorMessage = (payload as { detail?: string }).detail;
        throw new Error(errorMessage || "Unable to load reflection sources.");
      }

      setReflectionSources(
        Array.isArray(payload)
          ? payload.map((item) => ({
              ...item,
              id: String(item.id),
              text: item.text || "",
              daily_prompt: item.daily_prompt || null,
              source: item.source || null,
              created_at: item.created_at || null,
            }))
          : [],
      );
    } catch (error) {
      setSourcesError((error as Error).message || "Could not load reflection sources.");
    } finally {
      setSourcesBusy(false);
    }
  };

  const fetchPeopleOverview = async () => {
    setPeopleBusy(true);
    setPeopleError("");
    try {
      const response = await fetch(`${API_URL}/api/people`);
      const payload = (await response.json()) as PeopleOverviewPayload | { detail?: string };
      if (!response.ok) {
        const errorMessage = (payload as { detail?: string }).detail;
        throw new Error(errorMessage || "Unable to load people overview.");
      }
      setPeopleOverview(payload as PeopleOverviewPayload);
    } catch (error) {
      setPeopleOverview(null);
      setPeopleError((error as Error).message || "Could not load people overview.");
    } finally {
      setPeopleBusy(false);
    }
  };

  const onSelectTotal = async (selection: TotalSelection) => {
    setSelectedTotal(selection);
    if (selection === "reflections") {
      setPeopleBusy(false);
      setPeopleError("");
      setPeopleOverview(null);
      await fetchReflectionSources();
      return;
    }

    if (selection === "people") {
      setSourcesBusy(false);
      setSourcesError("");
      setReflectionSources([]);
      await fetchPeopleOverview();
      return;
    }

    setSourcesBusy(false);
    setSourcesError("");
    setReflectionSources([]);
    setPeopleBusy(false);
    setPeopleError("");
    setPeopleOverview(null);
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
          source: "app",
        }),
      });

      const payload = (await response.json()) as ReflectionResponse & { detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail || "Unable to run reflection");
      }

      setLastReflection(payload.result);
      setReflectionText("");
      setComposerOpen(false);
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

    setChatMessages((previous) => [...previous, userMessage]);
    setChatInput("");
    setChatBusy(true);

    // Add a placeholder assistant message that we'll stream into
    const placeholderIndex = chatMessages.length + 1; // +1 for the user message we just added
    setChatMessages((previous) => [...previous, { role: "assistant" as const, content: "" }]);

    try {
      const thread = chatThread ?? `chat-${Date.now()}`;
      const response = await fetch(`${API_URL}/api/chat/stream`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: userMessage.content, thread_id: thread }),
      });

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(errorBody || "Could not get response");
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response stream available");
      }

      const decoder = new TextDecoder();
      let accumulated = "";
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.slice(6);
          if (!jsonStr) continue;

          try {
            const event = JSON.parse(jsonStr) as { type: string; content: string };

            if (event.type === "thread_id") {
              setChatThread(event.content);
            } else if (event.type === "token") {
              accumulated += event.content;
              const snapshot = accumulated;
              setChatMessages((previous) => {
                const updated = [...previous];
                updated[placeholderIndex] = { role: "assistant", content: snapshot };
                return updated;
              });
            }
          } catch {
            // skip malformed SSE lines
          }
        }
      }

      // If nothing was streamed, show a fallback
      if (!accumulated) {
        setChatMessages((previous) => {
          const updated = [...previous];
          updated[placeholderIndex] = { role: "assistant", content: "No response returned." };
          return updated;
        });
      }
    } catch (error) {
      setChatMessages((previous) => {
        const updated = [...previous];
        updated[placeholderIndex] = {
          role: "assistant",
          content: (error as Error).message || "Something went wrong while chatting.",
        };
        return updated;
      });
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

  const totalCards = useMemo(
    () => [
      { key: "reflections" as const, label: "reflections", value: totals.reflections, icon: JournalIcon, color: "#ff7ea8" },
      { key: "patterns" as const, label: "patterns", value: totals.patterns, icon: PatternIcon, color: "#78a8ff" },
      { key: "emotions" as const, label: "emotions", value: totals.emotions, icon: EmotionIcon, color: "#ff6f7d" },
      { key: "themes" as const, label: "themes", value: totals.themes, icon: ThemeIcon, color: "#9f8bff" },
      { key: "people" as const, label: "people", value: totals.people, icon: PeopleIcon, color: "#ff9f58" },
      { key: "bodySignals" as const, label: "body signals", value: totals.bodySignals, icon: BodySignalIcon, color: "#35bda7" },
    ],
    [totals],
  );

  const visibleReflectionSources = useMemo(() => {
    const query = reflectionsQuery.trim().toLowerCase();
    const filtered = reflectionSources.filter((entry) => {
      const sourceMatch = reflectionsFilter === "all" || reflectionSourceKey(entry.source) === reflectionsFilter;
      if (!sourceMatch) {
        return false;
      }
      if (!query) {
        return true;
      }
      const body = `${entry.text || ""}\n${entry.daily_prompt || ""}`.toLowerCase();
      return body.includes(query);
    });

    const byDate = [...filtered].sort((a, b) => {
      const aTs = a.created_at ? Date.parse(a.created_at) : 0;
      const bTs = b.created_at ? Date.parse(b.created_at) : 0;
      return reflectionsSort === "newest" ? bTs - aTs : aTs - bTs;
    });

    return byDate;
  }, [reflectionSources, reflectionsFilter, reflectionsSort, reflectionsQuery]);

  const relationshipMix = useMemo(() => {
    if (!peopleOverview) {
      return [] as RelationshipMixEntry[];
    }
    return peopleOverview.relationship_mix.slice(0, 10);
  }, [peopleOverview]);

  const topTriggerPatterns = useMemo(() => {
    if (!peopleOverview) {
      return [] as TriggerPatternEntry[];
    }
    return peopleOverview.top_trigger_patterns.slice(0, 12);
  }, [peopleOverview]);

  return (
    <div className="app-shell">
      <main className="content">
        <header className="menubar">
          <span className="menubar-lotus" aria-label="Synapse home">
            <FlowerIcon className="menubar-lotus-icon" />
          </span>
          <nav className="menubar-stats" aria-label="Totals">
            {totalCards.map((item) => {
              const NavIcon: IconComponent = item.icon;
              return (
                <button
                  type="button"
                  key={item.key}
                  className={`menubar-stat ${selectedTotal === item.key ? "active" : ""}`}
                  aria-pressed={selectedTotal === item.key}
                  style={{ "--stat-color": item.color } as CSSProperties}
                  onClick={() => {
                    void onSelectTotal(item.key);
                  }}
                >
                  <span className="menubar-stat-emoji">
                    <NavIcon className="menubar-stat-icon" />
                  </span>
                  <span className="menubar-stat-number">{item.value}</span>
                  <span className="menubar-stat-label">{item.label}</span>
                </button>
              );
            })}
          </nav>
          <div className="menubar-time" aria-live="polite">
            {liveTime.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            })}
          </div>
        </header>

        <header className="hero">
          <p className="logo">synapse</p>
        </header>

        {selectedTotal ? (
          <section className="card panel">
            <div className="panel-head">
              <h2>
                {selectedTotal === "reflections" ? "All Reflections" : `${TOTAL_LABELS[selectedTotal]} source view`}
              </h2>
              <button type="button" onClick={() => setSelectedTotal(null)}>
                close
              </button>
            </div>

            {selectedTotal === "reflections" ? (
              <>
                {sourcesBusy ? <p className="muted">Loading all reflections...</p> : null}
                {sourcesError ? <p className="error">{sourcesError}</p> : null}
                {!sourcesBusy && !sourcesError && reflectionSources.length === 0 ? (
                  <p className="muted">No reflections found yet.</p>
                ) : null}

                {reflectionSources.length > 0 ? (
                  <>
                    <section className="reflection-source-controls" role="group" aria-label="Reflection list controls">
                      <label className="reflection-source-control">
                        <span>source</span>
                        <select
                          value={reflectionsFilter}
                          onChange={(event) =>
                            setReflectionsFilter(event.target.value as "all" | "app" | "telegram_text" | "voice")
                          }
                        >
                          <option value="all">all</option>
                          <option value="app">app</option>
                          <option value="telegram_text">telegram text</option>
                          <option value="voice">voice</option>
                        </select>
                      </label>
                      <label className="reflection-source-control">
                        <span>sort</span>
                        <select
                          value={reflectionsSort}
                          onChange={(event) => setReflectionsSort(event.target.value as "newest" | "oldest")}
                        >
                          <option value="newest">newest first</option>
                          <option value="oldest">oldest first</option>
                        </select>
                      </label>
                      <label className="reflection-source-control search">
                        <span>search</span>
                        <input
                          value={reflectionsQuery}
                          onChange={(event) => setReflectionsQuery(event.target.value)}
                          placeholder="find text or prompt"
                        />
                      </label>
                    </section>
                    <p className="reflection-source-summary">
                      Showing {visibleReflectionSources.length} of {reflectionSources.length}
                    </p>
                    {visibleReflectionSources.length === 0 ? (
                      <p className="muted">No reflections match your filters.</p>
                    ) : (
                      <section className="reflection-source-list">
                        {visibleReflectionSources.map((entry) => (
                          <article className="reflection-source-item" key={entry.id}>
                            <p className="reflection-source-meta">
                              {formatSourceDate(entry.created_at || null)} • {formatReflectionSource(entry.source)}
                            </p>
                            {entry.daily_prompt ? <p className="reflection-source-prompt">Prompt: {entry.daily_prompt}</p> : null}
                            <p>{entry.text}</p>
                          </article>
                        ))}
                      </section>
                    )}
                  </>
                ) : null}
              </>
            ) : null}

            {selectedTotal === "people" ? (
              <>
                {peopleBusy ? <p className="muted">Loading people graph...</p> : null}
                {peopleError ? <p className="error">{peopleError}</p> : null}
                {!peopleBusy && !peopleError && !peopleOverview?.people.length ? (
                  <p className="muted">No people found in the graph yet.</p>
                ) : null}

                {peopleOverview?.people.length ? (
                  <section className="people-drilldown">
                    <article className="people-key-action">
                      <p className="people-key-action-label">Key Action</p>
                      <p className="people-key-action-text">{peopleOverview.summary.key_action}</p>
                      <div className="people-kpi-row">
                        <p>
                          <strong>{peopleOverview.summary.total_people}</strong> people
                        </p>
                        <p>
                          <strong>{peopleOverview.summary.total_mentions}</strong> mentions
                        </p>
                        <p>
                          <strong>{peopleOverview.summary.unique_relationships}</strong> relationship types
                        </p>
                        <p>
                          Top:{" "}
                          <strong>
                            {peopleOverview.summary.top_person
                              ? `${peopleOverview.summary.top_person} (${peopleOverview.summary.top_person_mentions})`
                              : "n/a"}
                          </strong>
                        </p>
                      </div>
                    </article>

                    <div className="people-chart-grid">
                      <article className="panel compact">
                        <h3>Relationship Mix</h3>
                        {relationshipMix.length > 0 ? (
                          <ResponsiveContainer width="100%" height={220}>
                            <BarChart data={relationshipMix} layout="vertical">
                              <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                              <XAxis type="number" stroke={THEME_COLORS.muted} />
                              <YAxis
                                dataKey="relationship"
                                type="category"
                                width={120}
                                tickFormatter={(value) => titleCase(String(value))}
                                stroke={THEME_COLORS.muted}
                              />
                              <Tooltip {...CHART_TOOLTIP_STYLE} />
                              <Bar dataKey="mentions" radius={6} fill="#ff9f58" />
                            </BarChart>
                          </ResponsiveContainer>
                        ) : (
                          <p className="muted">No relationship data yet.</p>
                        )}
                      </article>

                      <article className="panel compact">
                        <h3>Top Triggered Patterns</h3>
                        {topTriggerPatterns.length > 0 ? (
                          <ResponsiveContainer width="100%" height={220}>
                            <BarChart data={topTriggerPatterns} layout="vertical">
                              <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                              <XAxis type="number" stroke={THEME_COLORS.muted} />
                              <YAxis dataKey="name" type="category" width={150} stroke={THEME_COLORS.muted} />
                              <Tooltip {...CHART_TOOLTIP_STYLE} />
                              <Bar dataKey="links" radius={6} fill="#8ab4f8" />
                            </BarChart>
                          </ResponsiveContainer>
                        ) : (
                          <p className="muted">No triggered patterns tracked yet.</p>
                        )}
                      </article>
                    </div>

                    <section className="people-list">
                      {peopleOverview.people.map((person) => (
                        <article key={person.id || person.name} className="people-item">
                          <div className="people-item-head">
                            <h3>{person.name}</h3>
                            <p className="meta">
                              {titleCase(person.relationship)} • {person.occurrences} mentions
                            </p>
                          </div>
                          {person.description ? <p>{person.description}</p> : null}
                          <p className="meta">
                            first seen {formatSourceDate(person.first_seen ?? null)} • last seen{" "}
                            {formatSourceDate(person.last_seen ?? null)}
                          </p>
                          {person.triggered_patterns.length > 0 ? (
                            <p>
                              <strong>Triggers:</strong>{" "}
                              {person.triggered_patterns.map((pattern) => `${pattern.name} (${pattern.links})`).join(", ")}
                            </p>
                          ) : (
                            <p className="muted">No linked patterns yet.</p>
                          )}
                        </article>
                      ))}
                    </section>
                  </section>
                ) : null}
              </>
            ) : null}

            {selectedTotal !== "reflections" && selectedTotal !== "people" ? (
              <p className="muted">
                Source drill-down for <strong>{TOTAL_LABELS[selectedTotal]}</strong> is not implemented yet.
              </p>
            ) : null}
          </section>
        ) : null}

        <nav className="tabs" role="tablist" aria-label="Primary tabs">
          <button
            type="button"
            className={activeTab === "reflect" ? "active" : ""}
            onClick={() => setActiveTab("reflect")}
          >
            reflect
          </button>
          <button
            type="button"
            className={activeTab === "patterns" ? "active" : ""}
            onClick={() => setActiveTab("patterns")}
          >
            patterns
          </button>
          <button
            type="button"
            className={activeTab === "ask" ? "active" : ""}
            onClick={() => setActiveTab("ask")}
          >
            ask
          </button>
        </nav>

        {activeTab === "reflect" ? (
          <section className="card reflect-card">
            <section className="prompt-row">
              <div className="prompt-head">
                <p className="prompt-label">Today&apos;s Prompt</p>
                <button
                  type="button"
                  className="prompt-refresh"
                  onClick={fetchPrompt}
                  title="Refresh prompt"
                  aria-label="Refresh daily prompt"
                >
                  <RefreshIcon className="prompt-refresh-icon" />
                </button>
              </div>
              <p className="prompt-text">{dailyPrompt || "Loading prompt..."}</p>
              <p className="prompt-cue">
                Start with a concrete moment, then describe what you noticed in your body, your thoughts, and any
                pattern that kept repeating.
              </p>
            </section>
            <div className="toolbar reflect-actions">
              <button
                type="button"
                onClick={() => {
                  setComposerOpen(true);
                  setReflectionError("");
                  setReflectionText(buildPromptDraft(dailyPrompt));
                }}
              >
                Use prompt
              </button>
              <button
                type="button"
                className="start-fresh-button"
                onClick={() => {
                  setComposerOpen(true);
                  setReflectionError("");
                  setReflectionText("");
                }}
              >
                Start fresh
              </button>
            </div>
            {composerOpen ? (
              <>
                <textarea
                  className="reflect-textarea"
                  rows={8}
                  value={reflectionText}
                  placeholder='Try writing in your own words: "What happened? What did I feel in my body? Where did I get reactive or calm?"'
                  onChange={(event) => setReflectionText(event.target.value)}
                />
                <div className="toolbar reflect-submit-wrap">
                  <button
                    type="button"
                    className="reflect-submit-button"
                    onClick={submitReflection}
                    disabled={reflectionBusy || !reflectionText.trim()}
                  >
                    reflect
                  </button>
                </div>
              </>
            ) : null}
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
