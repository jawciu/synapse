import { useEffect, useMemo, useState, type CSSProperties, type ComponentType, type KeyboardEvent, type SVGProps } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import AuthPage from "./pages/AuthPage";
import {
  Bar,
  BarChart,
  CartesianGrid,
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
  mentions?: number;
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
  mentions?: number;
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
  crisis_flag?: boolean;
};

type Summary = {
  total_reflections: number;
  total_patterns: number;
  total_emotions: number;
  total_themes: number;
  total_people: number;
  total_body_signals: number;
  top_patterns?: PatternEntry[];
  top_co_occurrences?: Array<{ pattern_a: string; pattern_b: string; times: number }>;
};

type DashboardPayload = {
  patterns_by_category: Record<string, PatternEntry[]>;
  themes: ThemeEntry[];
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

type View = "reflect" | "insights";
type ReflectMode = "journal" | "ask";

const API_URL = (import.meta as ImportMeta).env?.VITE_API_URL ?? "http://localhost:8000";
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

function roleName(value: string): string {
  return IF_ROLE_LABELS[value] ?? value;
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

const ASK_PROMPTS = [
  "What patterns keep showing up in my reflections?",
  "Which emotions come up most often for me?",
  "How are my relationships connected to my patterns?",
  "What does my body try to tell me when I'm stressed?",
  "Which themes link to my strongest emotions?",
  "What protective parts show up most in my writing?",
  "How have my patterns changed over time?",
  "What triggers my biggest emotional responses?",
];

function ReflectionProgress({ message }: { message: string }) {
  return (
    <div className="reflection-progress" key={message}>
      <div className="reflection-progress-inner">
        <FlowerIcon className="reflection-progress-icon" />
        <span className="reflection-progress-text">{message}</span>
      </div>
      <div className="reflection-progress-shimmer" />
    </div>
  );
}

function App() {
  const [authToken, setAuthToken] = useState<string | null>(() => localStorage.getItem("synapse_token"));
  const [authEmail, setAuthEmail] = useState<string | null>(() => localStorage.getItem("synapse_email"));

  const handleAuth = (result: { user_id: string; email: string; token: string }) => {
    localStorage.setItem("synapse_token", result.token);
    localStorage.setItem("synapse_email", result.email);
    setAuthToken(result.token);
    setAuthEmail(result.email);
  };

  const handleLogout = () => {
    localStorage.removeItem("synapse_token");
    localStorage.removeItem("synapse_email");
    setAuthToken(null);
    setAuthEmail(null);
  };

  const authHeaders = (): Record<string, string> =>
    authToken ? { Authorization: `Bearer ${authToken}` } : {};

  const [activeTab, setActiveTab] = useState<View>("reflect");
  const [reflectMode, setReflectMode] = useState<ReflectMode>("journal");
  const [askPromptIndex, setAskPromptIndex] = useState(0);
  const [avatarOpen, setAvatarOpen] = useState(false);

  useEffect(() => {
    if (!avatarOpen) return;
    const close = () => setAvatarOpen(false);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [avatarOpen]);
  const [dailyPrompt, setDailyPrompt] = useState("");
  const [reflectionText, setReflectionText] = useState("");
  const [reflectionBusy, setReflectionBusy] = useState(false);
  const [reflectionProgressMsg, setReflectionProgressMsg] = useState("Connecting...");
  const [reflectionError, setReflectionError] = useState("");
  const [lastReflection, setLastReflection] = useState<ReflectionPayload | null>(null);

  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null);
  const [dashboardBusy, setDashboardBusy] = useState(false);
  const [dashboardError, setDashboardError] = useState("");
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
    if (!authToken) return;
    const initialize = async () => {
      await fetchPrompt();
    };

    initialize();
  }, [authToken]);

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
      const promptResp = await fetch(`${API_URL}/api/daily-prompt`, { headers: authHeaders() });
      const promptJson = (await promptResp.json()) as { prompt?: string };
      setDailyPrompt(promptJson.prompt || "");
    } catch {
      setDailyPrompt("What felt most alive in your body today?");
    }
  };

  const fetchDashboard = async () => {
    setDashboardBusy(true);
    setDashboardError("");
    try {
      const res = await fetch(`${API_URL}/api/dashboard?limit=8`, { headers: authHeaders() });
      const payload = (await res.json()) as DashboardPayload | { detail?: string };
      if (!res.ok) {
        const errorMessage = (payload as { detail?: string }).detail;
        throw new Error(errorMessage || "Unable to load insights.");
      }
      setDashboard(payload as DashboardPayload);
    } catch (error) {
      setDashboardError((error as Error).message || "Could not load insights.");
    } finally {
      setDashboardBusy(false);
    }
  };

  const fetchReflectionSources = async () => {
    setSourcesBusy(true);
    setSourcesError("");
    try {
      const response = await fetch(`${API_URL}/api/reflections`, { headers: authHeaders() });
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
      const response = await fetch(`${API_URL}/api/people`, { headers: authHeaders() });
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

    if (selection === "patterns" || selection === "emotions" || selection === "themes" || selection === "bodySignals") {
      setSourcesBusy(false);
      setSourcesError("");
      setReflectionSources([]);
      setPeopleBusy(false);
      setPeopleError("");
      setPeopleOverview(null);
      await fetchDashboard();
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

    const textSnapshot = reflectionText;
    setReflectionBusy(true);
    setReflectionError("");
    setReflectionProgressMsg("Connecting...");

    try {
      const response = await fetch(`${API_URL}/api/reflection/stream`, {
        method: "POST",
        headers: { "content-type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          reflection_text: textSnapshot,
          daily_prompt: dailyPrompt || null,
          thread_id: null,
          source: "app",
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error((errData as Record<string, string>).detail || "Unable to run reflection");
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response stream");

      const decoder = new TextDecoder();
      let buffer = "";
      let payload: (ReflectionResponse & { detail?: string }) | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const evt = JSON.parse(line.slice(6)) as {
              type: string;
              content?: unknown;
              message?: string;
              node?: string;
            };
            if (evt.type === "progress" && evt.message) {
              setReflectionProgressMsg(evt.message);
            } else if (evt.type === "result" && evt.content) {
              payload = evt.content as ReflectionResponse & { detail?: string };
            }
          } catch {
            // skip malformed SSE lines
          }
        }
      }

      if (!payload) throw new Error("No result received from pipeline");

      // Safety net: force crisis_flag if input contains crisis keywords
      const lower = textSnapshot.toLowerCase();
      const crisisKeywords = [
        "kill myself", "kill myslef", "end my life", "end it all", "want to die",
        "wanna die", "suicide", "suicidal", "self-harm", "self harm", "hurt myself",
        "don't want to live", "dont want to live", "no reason to live",
      ];
      if (crisisKeywords.some((kw) => lower.includes(kw))) {
        if (payload.result.extracted) {
          payload.result.extracted.crisis_flag = true;
        }
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

  const onReflectionComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement | HTMLInputElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !reflectionBusy && reflectionText.trim()) {
      event.preventDefault();
      void submitReflection();
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

    setChatMessages((previous) => [
      ...previous,
      userMessage,
      { role: "assistant" as const, content: "" },
    ]);
    setChatInput("");
    setChatBusy(true);

    const updateLastAssistant = (content: string) => {
      setChatMessages((previous) => {
        const updated = [...previous];
        updated[updated.length - 1] = { role: "assistant", content };
        return updated;
      });
    };

    try {
      const thread = chatThread ?? `chat-${Date.now()}`;
      const response = await fetch(`${API_URL}/api/chat/stream`, {
        method: "POST",
        headers: { "content-type": "application/json", ...authHeaders() },
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
              updateLastAssistant(accumulated);
            }
          } catch {
            // skip malformed SSE lines
          }
        }
      }

      if (!accumulated) {
        updateLastAssistant("No response returned.");
      }
    } catch (error) {
      updateLastAssistant((error as Error).message || "Something went wrong while chatting.");
    } finally {
      setChatBusy(false);
    }
  };

  const extraction = useMemo<Extraction>(() => {
    return lastReflection?.extracted ? { ...EMPTY_EXTRACTION, ...lastReflection.extracted } : EMPTY_EXTRACTION;
  }, [lastReflection]);

  const insights = useMemo(() => lastReflection?.insights ?? "", [lastReflection]);
  const followUps = useMemo(() => lastReflection?.follow_up_questions ?? [], [lastReflection]);
  const hasEntityUpdates = useMemo(
    () =>
      extraction.patterns.length > 0 ||
      extraction.emotions.length > 0 ||
      extraction.themes.length > 0 ||
      extraction.ifs_parts.length > 0 ||
      extraction.schemas.length > 0 ||
      extraction.people.length > 0 ||
      extraction.body_signals.length > 0,
    [extraction],
  );

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

  const allPatterns = useMemo(() => {
    if (!dashboard) {
      return [] as PatternEntry[];
    }

    return Object.entries(dashboard.patterns_by_category ?? {})
      .flatMap(([category, rows]) =>
        (rows ?? []).map((row) => ({
          ...row,
          category: String(row.category || category || "other").toLowerCase(),
          occurrences: Number(row.occurrences || 0),
        })),
      )
      .sort((a, b) => b.occurrences - a.occurrences || a.name.localeCompare(b.name));
  }, [dashboard]);

  const patternCategoryMix = useMemo(() => {
    const buckets: Record<string, { category: string; patterns: number; mentions: number }> = {};
    for (const pattern of allPatterns) {
      const category = String(pattern.category || "other").toLowerCase();
      if (!buckets[category]) {
        buckets[category] = { category, patterns: 0, mentions: 0 };
      }
      buckets[category].patterns += 1;
      buckets[category].mentions += Number(pattern.occurrences || 0);
    }
    return Object.values(buckets).sort((a, b) => b.mentions - a.mentions || a.category.localeCompare(b.category));
  }, [allPatterns]);

  const topPatternPairs = useMemo(() => {
    return (dashboard?.summary.top_co_occurrences ?? [])
      .map((entry) => ({
        ...entry,
        label: `${entry.pattern_a} + ${entry.pattern_b}`,
      }))
      .slice(0, 10);
  }, [dashboard]);

  const patternSummary = useMemo(() => {
    const total_mentions = allPatterns.reduce((sum, pattern) => sum + Number(pattern.occurrences || 0), 0);
    const top_pattern = allPatterns[0] ?? null;
    const top_category = patternCategoryMix[0]?.category ?? null;
    const key_action = top_pattern
      ? `Pick one small experiment this week to interrupt '${top_pattern.name}' and journal what changed.`
      : "Add reflections so your strongest patterns can be surfaced.";
    return {
      total_patterns: allPatterns.length,
      total_mentions,
      top_pattern: top_pattern?.name ?? null,
      top_pattern_mentions: top_pattern?.occurrences ?? 0,
      top_category,
      key_action,
    };
  }, [allPatterns, patternCategoryMix]);

  const emotionList = useMemo(() => {
    if (!dashboard) {
      return [] as EmotionEntry[];
    }
    return [...dashboard.emotions]
      .map((emotion) => ({
        ...emotion,
        mentions: Number(emotion.mentions || 0),
        intensity: Number(emotion.intensity || 0),
        valence: String(emotion.valence || "neutral").toLowerCase(),
      }))
      .sort(
        (a, b) =>
          Number(b.mentions || 0) - Number(a.mentions || 0) ||
          Number(b.intensity || 0) - Number(a.intensity || 0) ||
          a.name.localeCompare(b.name),
      );
  }, [dashboard]);

  const emotionValenceMix = useMemo(() => {
    const buckets: Record<string, { valence: string; mentions: number; avg_intensity: number }> = {};
    for (const emotion of emotionList) {
      const valence = String(emotion.valence || "neutral").toLowerCase();
      if (!buckets[valence]) {
        buckets[valence] = { valence, mentions: 0, avg_intensity: 0 };
      }
      buckets[valence].mentions += Number(emotion.mentions || 0);
      buckets[valence].avg_intensity += Number(emotion.intensity || 0);
    }

    return Object.values(buckets)
      .map((bucket) => ({
        ...bucket,
        avg_intensity: bucket.mentions > 0 ? Number((bucket.avg_intensity / bucket.mentions).toFixed(3)) : 0,
      }))
      .sort((a, b) => b.mentions - a.mentions || a.valence.localeCompare(b.valence));
  }, [emotionList]);

  const emotionSummary = useMemo(() => {
    const total_mentions = emotionList.reduce((sum, emotion) => sum + Number(emotion.mentions || 0), 0);
    const top_emotion = emotionList[0] ?? null;
    const dominant_valence = emotionValenceMix[0]?.valence ?? null;
    const key_action = top_emotion
      ? `When '${top_emotion.name}' shows up next, pause for 90 seconds and name the emotion before reacting.`
      : "Add reflections so emotional trends can be surfaced.";
    return {
      total_emotions: emotionList.length,
      total_mentions,
      top_emotion: top_emotion?.name ?? null,
      top_emotion_mentions: Number(top_emotion?.mentions || 0),
      dominant_valence,
      key_action,
    };
  }, [emotionList, emotionValenceMix]);

  const themeList = useMemo(() => {
    if (!dashboard) {
      return [] as ThemeEntry[];
    }
    return [...dashboard.themes]
      .map((theme) => ({
        ...theme,
        name: String(theme.name || "").trim(),
        description: String(theme.description || "").trim(),
        mentions: Number(theme.mentions || 0),
      }))
      .filter((theme) => theme.name.length > 0)
      .sort((a, b) => Number(b.mentions || 0) - Number(a.mentions || 0) || a.name.localeCompare(b.name));
  }, [dashboard]);

  const themeSummary = useMemo(() => {
    const total_mentions = themeList.reduce((sum, theme) => sum + Number(theme.mentions || 0), 0);
    const top_theme = themeList[0] ?? null;
    const key_action = top_theme
      ? `Use '${top_theme.name}' as your journaling lens for the next 3 entries and note any shift.`
      : "Add reflections so recurring life themes can be surfaced.";
    return {
      total_themes: themeList.length,
      total_mentions,
      top_theme: top_theme?.name ?? null,
      top_theme_mentions: Number(top_theme?.mentions || 0),
      key_action,
    };
  }, [themeList]);

  const bodySignalList = useMemo(() => {
    if (!dashboard) {
      return [] as BodySignal[];
    }
    return [...dashboard.body_signals]
      .map((signal) => ({
        ...signal,
        name: String(signal.name || "").trim(),
        location: String(signal.location || "other").trim().toLowerCase(),
        occurrences: Number(signal.occurrences || 0),
      }))
      .filter((signal) => signal.name.length > 0)
      .sort((a, b) => b.occurrences - a.occurrences || a.name.localeCompare(b.name));
  }, [dashboard]);

  const bodyLocationMix = useMemo(() => {
    const buckets: Record<string, { location: string; signals: number; occurrences: number }> = {};
    for (const signal of bodySignalList) {
      const location = signal.location || "other";
      if (!buckets[location]) {
        buckets[location] = { location, signals: 0, occurrences: 0 };
      }
      buckets[location].signals += 1;
      buckets[location].occurrences += Number(signal.occurrences || 0);
    }
    return Object.values(buckets).sort((a, b) => b.occurrences - a.occurrences || a.location.localeCompare(b.location));
  }, [bodySignalList]);

  const bodySummary = useMemo(() => {
    const total_occurrences = bodySignalList.reduce((sum, signal) => sum + Number(signal.occurrences || 0), 0);
    const top_signal = bodySignalList[0] ?? null;
    const top_location = bodyLocationMix[0]?.location ?? null;
    const key_action = top_signal
      ? `The next time '${top_signal.name}' appears, take one slow breath and label what emotion is present.`
      : "Add reflections with body sensations so somatic patterns can be surfaced.";
    return {
      total_signals: bodySignalList.length,
      total_occurrences,
      top_signal: top_signal?.name ?? null,
      top_signal_occurrences: top_signal?.occurrences ?? 0,
      top_location,
      key_action,
    };
  }, [bodySignalList, bodyLocationMix]);

  const hasChatHistory = chatMessages.length > 0;

  if (!authToken) {
    return <AuthPage onAuth={handleAuth} />;
  }

  return (
    <div className="app-shell">
      <main className="content">
        <header className="topbar">
          <div className="topbar-left">
            <FlowerIcon className="topbar-logo-icon" />
            <span className="topbar-logotype">synapse</span>
          </div>
          <nav className="topbar-nav" role="tablist">
            <button
              type="button"
              className={`topbar-nav-link ${activeTab === "reflect" ? "active" : ""}`}
              onClick={() => { setActiveTab("reflect"); setSelectedTotal(null); }}
            >
              reflect
            </button>
            <button
              type="button"
              className={`topbar-nav-link ${activeTab === "insights" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("insights");
                setSelectedTotal(null);
                if (!dashboard && !dashboardBusy) {
                  void fetchDashboard();
                }
                if (reflectionSources.length === 0 && !sourcesBusy) {
                  void fetchReflectionSources();
                }
              }}
            >
              insights
            </button>
          </nav>
          <div className="topbar-right">
            <button
              type="button"
              className="topbar-avatar"
              onClick={(e) => { e.stopPropagation(); setAvatarOpen((prev) => !prev); }}
              title={authEmail || "Account"}
            >
              {(authEmail || "?")[0].toUpperCase()}
            </button>
            {avatarOpen ? (
              <div className="topbar-popover">
                <p className="topbar-popover-email">{authEmail}</p>
                <button
                  type="button"
                  className="topbar-popover-logout"
                  onClick={() => { setAvatarOpen(false); handleLogout(); }}
                >
                  Log out
                </button>
              </div>
            ) : null}
          </div>
        </header>

        {activeTab === "insights" ? (
          <>
            {!selectedTotal ? (
              dashboardBusy && !dashboard ? (
                <section className="card panel">
                  <p className="muted">Loading insights...</p>
                </section>
              ) : (
              <>
              {dashboardError ? <p className="error">{dashboardError}</p> : null}
              <section className="insights-tiles">
                {/* Reflections tile */}
                <div
                  className="insight-tile"
                  style={{ "--tile-color": "#ff7ea8" } as CSSProperties}
                  onClick={() => { void onSelectTotal("reflections"); }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="insight-tile-header">
                    <JournalIcon className="insight-tile-icon" />
                    <span className="insight-tile-number">{totals.reflections}</span>
                    <span className="insight-tile-label">reflections</span>
                  </div>
                  <div className="insight-tile-preview">
                    {reflectionSources.length > 0 ? (
                      <p className="insight-tile-excerpt">{reflectionSources[0].text}</p>
                    ) : (
                      <p className="insight-tile-empty">No reflections yet</p>
                    )}
                  </div>
                </div>

                {/* Patterns tile */}
                <div
                  className="insight-tile"
                  style={{ "--tile-color": "#78a8ff" } as CSSProperties}
                  onClick={() => { void onSelectTotal("patterns"); }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="insight-tile-header">
                    <PatternIcon className="insight-tile-icon" />
                    <span className="insight-tile-number">{totals.patterns}</span>
                    <span className="insight-tile-label">patterns</span>
                  </div>
                  <div className="insight-tile-preview">
                    {patternCategoryMix.length > 0 ? (
                      <ResponsiveContainer width="100%" height={130}>
                        <BarChart data={patternCategoryMix} layout="vertical" margin={{ left: 0, right: 0, top: 0, bottom: 0 }}>
                          <XAxis type="number" hide />
                          <YAxis dataKey="category" type="category" width={80} tick={{ fontSize: 11 }} stroke={THEME_COLORS.muted} tickFormatter={(v) => titleCase(String(v))} />
                          <Bar dataKey="mentions" radius={4} fill="#78a8ff" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="insight-tile-empty">No patterns yet</p>
                    )}
                  </div>
                </div>

                {/* Emotions tile */}
                <div
                  className="insight-tile"
                  style={{ "--tile-color": "#ff6f7d" } as CSSProperties}
                  onClick={() => { void onSelectTotal("emotions"); }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="insight-tile-header">
                    <EmotionIcon className="insight-tile-icon" />
                    <span className="insight-tile-number">{totals.emotions}</span>
                    <span className="insight-tile-label">emotions</span>
                  </div>
                  <div className="insight-tile-preview">
                    {emotionList.length > 0 ? (
                      <ResponsiveContainer width="100%" height={130}>
                        <BarChart data={emotionList.slice(0, 5)} layout="vertical" margin={{ left: 0, right: 0, top: 0, bottom: 0 }}>
                          <XAxis type="number" hide />
                          <YAxis dataKey="name" type="category" width={80} tick={{ fontSize: 11 }} stroke={THEME_COLORS.muted} />
                          <Bar dataKey="mentions" radius={4} fill="#ff6f7d" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="insight-tile-empty">No emotions yet</p>
                    )}
                  </div>
                </div>

                {/* Themes tile */}
                <div
                  className="insight-tile"
                  style={{ "--tile-color": "#9f8bff" } as CSSProperties}
                  onClick={() => { void onSelectTotal("themes"); }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="insight-tile-header">
                    <ThemeIcon className="insight-tile-icon" />
                    <span className="insight-tile-number">{totals.themes}</span>
                    <span className="insight-tile-label">themes</span>
                  </div>
                  <div className="insight-tile-preview">
                    {themeList.length > 0 ? (
                      <ResponsiveContainer width="100%" height={130}>
                        <BarChart data={themeList.slice(0, 5)} layout="vertical" margin={{ left: 0, right: 0, top: 0, bottom: 0 }}>
                          <XAxis type="number" hide />
                          <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 11 }} stroke={THEME_COLORS.muted} />
                          <Bar dataKey="mentions" radius={4} fill="#9f8bff" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="insight-tile-empty">No themes yet</p>
                    )}
                  </div>
                </div>

                {/* People tile */}
                <div
                  className="insight-tile"
                  style={{ "--tile-color": "#ff9f58" } as CSSProperties}
                  onClick={() => { void onSelectTotal("people"); }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="insight-tile-header">
                    <PeopleIcon className="insight-tile-icon" />
                    <span className="insight-tile-number">{totals.people}</span>
                    <span className="insight-tile-label">people</span>
                  </div>
                  <div className="insight-tile-preview">
                    {dashboard?.people && dashboard.people.length > 0 ? (
                      <ResponsiveContainer width="100%" height={130}>
                        <BarChart data={dashboard.people.slice(0, 5)} layout="vertical" margin={{ left: 0, right: 0, top: 0, bottom: 0 }}>
                          <XAxis type="number" hide />
                          <YAxis dataKey="name" type="category" width={80} tick={{ fontSize: 11 }} stroke={THEME_COLORS.muted} />
                          <Bar dataKey="occurrences" radius={4} fill="#ff9f58" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="insight-tile-empty">No people yet</p>
                    )}
                  </div>
                </div>

                {/* Body Signals tile */}
                <div
                  className="insight-tile"
                  style={{ "--tile-color": "#35bda7" } as CSSProperties}
                  onClick={() => { void onSelectTotal("bodySignals"); }}
                  role="button"
                  tabIndex={0}
                >
                  <div className="insight-tile-header">
                    <BodySignalIcon className="insight-tile-icon" />
                    <span className="insight-tile-number">{totals.bodySignals}</span>
                    <span className="insight-tile-label">body signals</span>
                  </div>
                  <div className="insight-tile-preview">
                    {bodyLocationMix.length > 0 ? (
                      <ResponsiveContainer width="100%" height={130}>
                        <BarChart data={bodyLocationMix.slice(0, 5)} layout="vertical" margin={{ left: 0, right: 0, top: 0, bottom: 0 }}>
                          <XAxis type="number" hide />
                          <YAxis dataKey="location" type="category" width={80} tick={{ fontSize: 11 }} stroke={THEME_COLORS.muted} tickFormatter={(v) => titleCase(String(v))} />
                          <Bar dataKey="occurrences" radius={4} fill="#35bda7" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="insight-tile-empty">No body signals yet</p>
                    )}
                  </div>
                </div>
              </section>
              </>
              )
            ) : (
              <section className="card panel">
                <div className="panel-head">
                  <h2>{selectedTotal === "reflections" ? "All Reflections" : titleCase(TOTAL_LABELS[selectedTotal])}</h2>
                  <button type="button" onClick={() => setSelectedTotal(null)}>
                    back
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
                          <ResponsiveContainer width="100%" height={Math.max(220, relationshipMix.length * 36)}>
                            <BarChart data={relationshipMix} layout="vertical">
                              <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                              <XAxis type="number" stroke={THEME_COLORS.muted} />
                              <YAxis
                                dataKey="relationship"
                                type="category"
                                width={120}
                                interval={0}
                                tick={{ fontSize: 11 }}
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
                          <ResponsiveContainer width="100%" height={Math.max(220, topTriggerPatterns.length * 36)}>
                            <BarChart data={topTriggerPatterns} layout="vertical">
                              <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                              <XAxis type="number" stroke={THEME_COLORS.muted} />
                              <YAxis dataKey="name" type="category" width={150} tick={{ fontSize: 11 }} interval={0} stroke={THEME_COLORS.muted} />
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

            {selectedTotal === "patterns" ? (
              <section className="people-drilldown">
                <article className="people-key-action">
                  <p className="people-key-action-label">Key Action</p>
                  <p className="people-key-action-text">{patternSummary.key_action}</p>
                  <div className="people-kpi-row">
                    <p>
                      <strong>{patternSummary.total_patterns}</strong> patterns
                    </p>
                    <p>
                      <strong>{patternSummary.total_mentions}</strong> mentions
                    </p>
                    <p>
                      Top category: <strong>{patternSummary.top_category ? titleCase(patternSummary.top_category) : "n/a"}</strong>
                    </p>
                    <p>
                      Top pattern:{" "}
                      <strong>
                        {patternSummary.top_pattern
                          ? `${patternSummary.top_pattern} (${patternSummary.top_pattern_mentions})`
                          : "n/a"}
                      </strong>
                    </p>
                  </div>
                </article>

                <div className="people-chart-grid">
                  <article className="panel compact">
                    <h3>Category Mix</h3>
                    {patternCategoryMix.length > 0 ? (
                      <ResponsiveContainer width="100%" height={Math.max(220, patternCategoryMix.length * 36)}>
                        <BarChart data={patternCategoryMix} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                          <XAxis type="number" stroke={THEME_COLORS.muted} />
                          <YAxis
                            dataKey="category"
                            type="category"
                            width={130}
                            interval={0}
                            tick={{ fontSize: 11 }}
                            tickFormatter={(value) => titleCase(String(value))}
                            stroke={THEME_COLORS.muted}
                          />
                          <Tooltip {...CHART_TOOLTIP_STYLE} />
                          <Bar dataKey="mentions" radius={6} fill="#78a8ff" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="muted">No pattern data yet.</p>
                    )}
                  </article>

                  <article className="panel compact">
                    <h3>Top Co-occurrences</h3>
                    {topPatternPairs.length > 0 ? (
                      <ResponsiveContainer width="100%" height={Math.max(220, topPatternPairs.length * 44)}>
                        <BarChart data={topPatternPairs} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                          <XAxis type="number" stroke={THEME_COLORS.muted} />
                          <YAxis dataKey="label" type="category" width={190} tick={{ fontSize: 10 }} interval={0} stroke={THEME_COLORS.muted} />
                          <Tooltip {...CHART_TOOLTIP_STYLE} />
                          <Bar dataKey="times" radius={6} fill="#9f8bff" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="muted">No co-occurrence data yet.</p>
                    )}
                  </article>
                </div>

                <section className="people-list">
                  {allPatterns.length > 0 ? (
                    allPatterns.map((pattern) => (
                      <article key={`${pattern.category}-${pattern.name}`} className="people-item">
                        <div className="people-item-head">
                          <h3>{pattern.name}</h3>
                          <p className="meta">
                            {titleCase(pattern.category)} • {pattern.occurrences} mentions
                          </p>
                        </div>
                        {pattern.description ? <p>{pattern.description}</p> : <p className="muted">No description yet.</p>}
                      </article>
                    ))
                  ) : (
                    <p className="muted">No patterns found yet.</p>
                  )}
                </section>
              </section>
            ) : null}

            {selectedTotal === "emotions" ? (
              <section className="people-drilldown">
                <article className="people-key-action">
                  <p className="people-key-action-label">Key Action</p>
                  <p className="people-key-action-text">{emotionSummary.key_action}</p>
                  <div className="people-kpi-row">
                    <p>
                      <strong>{emotionSummary.total_emotions}</strong> emotions
                    </p>
                    <p>
                      <strong>{emotionSummary.total_mentions}</strong> mentions
                    </p>
                    <p>
                      Dominant valence: <strong>{emotionSummary.dominant_valence ? titleCase(emotionSummary.dominant_valence) : "n/a"}</strong>
                    </p>
                    <p>
                      Top emotion:{" "}
                      <strong>
                        {emotionSummary.top_emotion
                          ? `${emotionSummary.top_emotion} (${emotionSummary.top_emotion_mentions})`
                          : "n/a"}
                      </strong>
                    </p>
                  </div>
                </article>

                <div className="people-chart-grid">
                  <article className="panel compact">
                    <h3>Valence Mix</h3>
                    {emotionValenceMix.length > 0 ? (
                      <ResponsiveContainer width="100%" height={Math.max(220, emotionValenceMix.length * 36)}>
                        <BarChart data={emotionValenceMix} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                          <XAxis type="number" stroke={THEME_COLORS.muted} />
                          <YAxis
                            dataKey="valence"
                            type="category"
                            width={130}
                            interval={0}
                            tick={{ fontSize: 11 }}
                            tickFormatter={(value) => titleCase(String(value))}
                            stroke={THEME_COLORS.muted}
                          />
                          <Tooltip {...CHART_TOOLTIP_STYLE} />
                          <Bar dataKey="mentions" radius={6} fill="#ff6f7d" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="muted">No valence data yet.</p>
                    )}
                  </article>

                  <article className="panel compact">
                    <h3>Top Emotions</h3>
                    {emotionList.length > 0 ? (
                      <ResponsiveContainer width="100%" height={Math.max(220, Math.min(emotionList.length, 12) * 36)}>
                        <BarChart data={emotionList.slice(0, 12)} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                          <XAxis type="number" stroke={THEME_COLORS.muted} />
                          <YAxis dataKey="name" type="category" width={150} tick={{ fontSize: 11 }} interval={0} stroke={THEME_COLORS.muted} />
                          <Tooltip {...CHART_TOOLTIP_STYLE} />
                          <Bar dataKey="mentions" radius={6} fill="#f2a6a6" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="muted">No emotion data yet.</p>
                    )}
                  </article>
                </div>

                <section className="people-list">
                  {emotionList.length > 0 ? (
                    emotionList.map((emotion) => (
                      <article key={emotion.name} className="people-item">
                        <div className="people-item-head">
                          <h3>{emotion.name}</h3>
                          <p className="meta">
                            {titleCase(emotion.valence)} • {Number(emotion.mentions || 0)} mentions
                          </p>
                        </div>
                        <p className="meta">intensity {clampPercent(Number(emotion.intensity || 0))}%</p>
                      </article>
                    ))
                  ) : (
                    <p className="muted">No emotions found yet.</p>
                  )}
                </section>
              </section>
            ) : null}

            {selectedTotal === "themes" ? (
              <section className="people-drilldown">
                <article className="people-key-action">
                  <p className="people-key-action-label">Key Action</p>
                  <p className="people-key-action-text">{themeSummary.key_action}</p>
                  <div className="people-kpi-row">
                    <p>
                      <strong>{themeSummary.total_themes}</strong> themes
                    </p>
                    <p>
                      <strong>{themeSummary.total_mentions}</strong> mentions
                    </p>
                    <p>
                      Top theme:{" "}
                      <strong>
                        {themeSummary.top_theme ? `${themeSummary.top_theme} (${themeSummary.top_theme_mentions})` : "n/a"}
                      </strong>
                    </p>
                  </div>
                </article>

                <article className="panel compact">
                  <h3>Theme Mentions</h3>
                  {themeList.length > 0 ? (
                    <ResponsiveContainer width="100%" height={Math.max(240, Math.min(themeList.length, 12) * 36)}>
                      <BarChart data={themeList.slice(0, 12)} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                        <XAxis type="number" stroke={THEME_COLORS.muted} />
                        <YAxis dataKey="name" type="category" width={170} tick={{ fontSize: 11 }} interval={0} stroke={THEME_COLORS.muted} />
                        <Tooltip {...CHART_TOOLTIP_STYLE} />
                        <Bar dataKey="mentions" radius={6} fill="#9f8bff" />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="muted">No themes found yet.</p>
                  )}
                </article>

                <section className="people-list">
                  {themeList.length > 0 ? (
                    themeList.map((theme) => (
                      <article key={theme.name} className="people-item">
                        <div className="people-item-head">
                          <h3>{theme.name}</h3>
                          <p className="meta">{Number(theme.mentions || 0)} mentions</p>
                        </div>
                        {theme.description ? <p>{theme.description}</p> : <p className="muted">No description yet.</p>}
                      </article>
                    ))
                  ) : (
                    <p className="muted">No themes found yet.</p>
                  )}
                </section>
              </section>
            ) : null}

            {selectedTotal === "bodySignals" ? (
              <section className="people-drilldown">
                <article className="people-key-action">
                  <p className="people-key-action-label">Key Action</p>
                  <p className="people-key-action-text">{bodySummary.key_action}</p>
                  <div className="people-kpi-row">
                    <p>
                      <strong>{bodySummary.total_signals}</strong> body signals
                    </p>
                    <p>
                      <strong>{bodySummary.total_occurrences}</strong> occurrences
                    </p>
                    <p>
                      Top location: <strong>{bodySummary.top_location ? titleCase(bodySummary.top_location) : "n/a"}</strong>
                    </p>
                    <p>
                      Top signal:{" "}
                      <strong>
                        {bodySummary.top_signal ? `${bodySummary.top_signal} (${bodySummary.top_signal_occurrences})` : "n/a"}
                      </strong>
                    </p>
                  </div>
                </article>

                <div className="people-chart-grid">
                  <article className="panel compact">
                    <h3>Location Mix</h3>
                    {bodyLocationMix.length > 0 ? (
                      <ResponsiveContainer width="100%" height={Math.max(220, bodyLocationMix.length * 36)}>
                        <BarChart data={bodyLocationMix} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                          <XAxis type="number" stroke={THEME_COLORS.muted} />
                          <YAxis
                            dataKey="location"
                            type="category"
                            width={130}
                            interval={0}
                            tick={{ fontSize: 11 }}
                            tickFormatter={(value) => titleCase(String(value))}
                            stroke={THEME_COLORS.muted}
                          />
                          <Tooltip {...CHART_TOOLTIP_STYLE} />
                          <Bar dataKey="occurrences" radius={6} fill="#35bda7" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="muted">No body-signal data yet.</p>
                    )}
                  </article>

                  <article className="panel compact">
                    <h3>Top Body Signals</h3>
                    {bodySignalList.length > 0 ? (
                      <ResponsiveContainer width="100%" height={Math.max(220, Math.min(bodySignalList.length, 12) * 36)}>
                        <BarChart data={bodySignalList.slice(0, 12)} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                          <XAxis type="number" stroke={THEME_COLORS.muted} />
                          <YAxis dataKey="name" type="category" width={160} tick={{ fontSize: 11 }} interval={0} stroke={THEME_COLORS.muted} />
                          <Tooltip {...CHART_TOOLTIP_STYLE} />
                          <Bar dataKey="occurrences" radius={6} fill="#6ad1c0" />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <p className="muted">No body signals found yet.</p>
                    )}
                  </article>
                </div>

                <section className="people-list">
                  {bodySignalList.length > 0 ? (
                    bodySignalList.map((signal) => (
                      <article key={signal.name} className="people-item">
                        <div className="people-item-head">
                          <h3>{signal.name}</h3>
                          <p className="meta">
                            {titleCase(signal.location)} • {signal.occurrences} occurrences
                          </p>
                        </div>
                      </article>
                    ))
                  ) : (
                    <p className="muted">No body signals found yet.</p>
                  )}
                </section>
              </section>
            ) : null}
              </section>
            )}
          </>
        ) : null}

        {activeTab === "reflect" ? (
          <section className="reflect-section">
            <p className="reflect-greeting">Map your mind. Understand yourself.</p>

            <div className="reflect-mode-toggle">
              <button
                type="button"
                className={`reflect-mode-btn ${reflectMode === "journal" ? "active" : ""}`}
                onClick={() => setReflectMode("journal")}
              >
                Journal
              </button>
              <button
                type="button"
                className={`reflect-mode-btn ${reflectMode === "ask" ? "active" : ""}`}
                onClick={() => setReflectMode("ask")}
              >
                Ask a question
              </button>
            </div>

            <div className="reflect-prompt-display">
              <p className="reflect-prompt-text">
                {reflectMode === "journal" ? (dailyPrompt || "What felt most alive in your body today?") : ASK_PROMPTS[askPromptIndex]}
              </p>
              <button
                type="button"
                className="reflect-prompt-use"
                onClick={() => {
                  if (reflectMode === "journal") {
                    setReflectionText(buildPromptDraft(dailyPrompt));
                  } else {
                    setChatInput(ASK_PROMPTS[askPromptIndex]);
                  }
                }}
              >
                Use this prompt
              </button>
              <button
                type="button"
                className="reflect-prompt-refresh"
                onClick={() => {
                  if (reflectMode === "journal") {
                    void fetchPrompt();
                  } else {
                    setAskPromptIndex((prev) => (prev + 1) % ASK_PROMPTS.length);
                  }
                }}
                title="Try another prompt"
              >
                <RefreshIcon className="reflect-prompt-refresh-icon" />
              </button>
            </div>

            {reflectMode === "journal" ? (
              <>
                <textarea
                  className="reflect-textarea"
                  rows={6}
                  value={reflectionText}
                  placeholder='Write freely — what happened, what you felt in your body, any pattern you noticed...'
                  onChange={(event) => setReflectionText(event.target.value)}
                  onKeyDown={onReflectionComposerKeyDown}
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
                {reflectionBusy ? <ReflectionProgress message={reflectionProgressMsg} /> : null}
                {reflectionError ? <p className="error">{reflectionError}</p> : null}

                {lastReflection ? (
                  extraction.crisis_flag ? (
                    <section className="crisis-card">
                      <p className="crisis-message">{insights}</p>
                      <div className="crisis-helplines">
                        <h3>Crisis helplines</h3>
                        <p><strong>UK:</strong> Samaritans — call <a href="tel:116123">116 123</a> (free, 24/7) or text SHOUT to <strong>85258</strong></p>
                        <p><strong>US:</strong> 988 Suicide &amp; Crisis Lifeline — call or text <a href="tel:988"><strong>988</strong></a></p>
                        <p><strong>International:</strong> <a href="https://findahelpline.com" target="_blank" rel="noopener noreferrer">findahelpline.com</a></p>
                      </div>
                    </section>
                  ) : (
                    <>
                      {hasEntityUpdates ? (
                        <div className="result-grid">
                          {extraction.patterns.length > 0 ? (
                            <section className="panel">
                              <h3>Patterns</h3>
                              {extraction.patterns.map((pattern) => (
                                <p key={pattern.name}>
                                  <strong>{pattern.name}</strong> <span className="meta">({pattern.category})</span> -{' '}
                                  {clampPercent(pattern.strength)}%
                                </p>
                              ))}
                            </section>
                          ) : null}

                          {extraction.emotions.length > 0 ? (
                            <section className="panel">
                              <h3>Emotions</h3>
                              {extraction.emotions.map((emotion) => (
                                <p key={emotion.name}>
                                  <strong>{emotion.name}</strong> <span className="meta">({emotion.valence})</span> -{' '}
                                  {clampPercent(emotion.intensity)}%
                                </p>
                              ))}
                            </section>
                          ) : null}

                          {extraction.themes.length > 0 ? (
                            <section className="panel">
                              <h3>Themes</h3>
                              {extraction.themes.map((theme) => (
                                <p key={theme.name}>
                                  <strong>{theme.name}</strong>
                                  <span className="muted"> - {theme.description}</span>
                                </p>
                              ))}
                            </section>
                          ) : null}

                          {extraction.ifs_parts.length > 0 ? (
                            <section className="panel">
                              <h3>IFS Parts</h3>
                              {extraction.ifs_parts.map((part) => (
                                <p key={part.name}>
                                  <strong>{part.name}</strong> <span className="meta">({roleName(part.role)})</span>
                                  <span className="muted"> - {part.description}</span>
                                </p>
                              ))}
                            </section>
                          ) : null}

                          {extraction.schemas.length > 0 ? (
                            <section className="panel">
                              <h3>Schemas</h3>
                              {extraction.schemas.map((schema) => (
                                <p key={schema.name}>
                                  <strong>{schema.name}</strong>
                                  <span className="meta">
                                    ({SCHEMA_DOMAIN_LABELS[schema.domain] || schema.domain}, {COPING_LABELS[schema.coping_style] || schema.coping_style})
                                  </span>
                                  <span className="muted"> - {schema.description}</span>
                                </p>
                              ))}
                            </section>
                          ) : null}

                          {extraction.people.length > 0 ? (
                            <section className="panel">
                              <h3>People</h3>
                              {extraction.people.map((person) => (
                                <p key={person.name}>
                                  <strong>{person.name}</strong>
                                  <span className="meta"> ({person.relationship})</span>
                                  {person.description ? <span className="muted"> - {person.description}</span> : null}
                                </p>
                              ))}
                            </section>
                          ) : null}

                          {extraction.body_signals.length > 0 ? (
                            <section className="panel">
                              <h3>Body Signals</h3>
                              {extraction.body_signals.map((signal) => (
                                <p key={signal.name}>
                                  <strong>{signal.name}</strong>
                                  <span className="meta"> ({signal.location})</span>
                                </p>
                              ))}
                            </section>
                          ) : null}
                        </div>
                      ) : null}

                      <div className="result-grid">
                        <section className="panel wide-panel">
                          <h3>Insights</h3>
                          <p>{insights || "--"}</p>
                        </section>

                        {followUps.length > 0 ? (
                          <section className="panel wide-panel">
                            <h3>Follow-up Questions</h3>
                            <ul>
                              {followUps.map((followUp) => (
                                <li key={followUp}>{followUp}</li>
                              ))}
                            </ul>
                          </section>
                        ) : null}
                      </div>
                    </>
                  )
                ) : null}
              </>
            ) : (
              <>
                {hasChatHistory ? (
                  <div className="chat-log">
                    {chatMessages.map((message, index) => (
                      <div key={`${message.role}-${index}`} className={`chat-line ${message.role}`}>
                        <strong>{message.role === "user" ? "You" : "synapse"}:</strong>
                        {message.role === "user" ? (
                          <span> {message.content}</span>
                        ) : (
                          <Markdown remarkPlugins={[remarkGfm]}>{message.content}</Markdown>
                        )}
                      </div>
                    ))}
                    {chatBusy && chatMessages.length > 0 && !chatMessages[chatMessages.length - 1].content ? (
                      <div className="chat-thinking">
                        <span className="chat-thinking-text">Assistant is thinking...</span>
                        <div className="chat-thinking-shimmer" />
                      </div>
                    ) : null}
                  </div>
                ) : null}
                <textarea
                  className="reflect-textarea"
                  rows={6}
                  value={chatInput}
                  placeholder="Ask anything about your patterns, emotions, or reflections..."
                  onChange={(event) => setChatInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey && !chatBusy && chatInput.trim()) {
                      event.preventDefault();
                      void sendChat();
                    }
                  }}
                />
                <div className="toolbar reflect-submit-wrap">
                  <button
                    type="button"
                    className="reflect-submit-button"
                    onClick={sendChat}
                    disabled={chatBusy || !chatInput.trim()}
                  >
                    ask
                  </button>
                </div>
              </>
            )}
          </section>
        ) : null}
      </main>
    </div>
  );
}

export { App };
