import { useEffect, useMemo, useState, type CSSProperties, type ComponentType, type KeyboardEvent, type SVGProps } from "react";
import Markdown from "react-markdown";
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

type View = "reflect" | "ask";

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
  const [dailyPrompt, setDailyPrompt] = useState("");
  const [reflectionText, setReflectionText] = useState("");
  const [composerOpen, setComposerOpen] = useState(false);
  const [composerVariant, setComposerVariant] = useState<"prompt" | "fresh">("prompt");
  const [reflectionBusy, setReflectionBusy] = useState(false);
  const [reflectionError, setReflectionError] = useState("");
  const [lastReflection, setLastReflection] = useState<ReflectionPayload | null>(null);

  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null);
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
      await fetchDashboard();
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
    try {
      const res = await fetch(`${API_URL}/api/dashboard?limit=8`, { headers: authHeaders() });
      const payload = (await res.json()) as DashboardPayload;
      setDashboard(payload);
    } catch {
      setDashboard({
        patterns_by_category: { cognitive: [], emotional: [], relational: [], behavioral: [] },
        themes: [],
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

    setReflectionBusy(true);
    setReflectionError("");

    try {
      const response = await fetch(`${API_URL}/api/reflection`, {
        method: "POST",
        headers: { "content-type": "application/json", ...authHeaders() },
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

  const onReflectionComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement | HTMLInputElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter" && !reflectionBusy && reflectionText.trim()) {
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
          <div className="menubar-user">
            {authEmail && <span className="menubar-email">{authEmail}</span>}
            <button type="button" className="menubar-logout" onClick={handleLogout}>
              log out
            </button>
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
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={patternCategoryMix} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                          <XAxis type="number" stroke={THEME_COLORS.muted} />
                          <YAxis
                            dataKey="category"
                            type="category"
                            width={130}
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
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={topPatternPairs} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                          <XAxis type="number" stroke={THEME_COLORS.muted} />
                          <YAxis dataKey="label" type="category" width={170} stroke={THEME_COLORS.muted} />
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
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={emotionValenceMix} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                          <XAxis type="number" stroke={THEME_COLORS.muted} />
                          <YAxis
                            dataKey="valence"
                            type="category"
                            width={130}
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
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={emotionList.slice(0, 12)} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                          <XAxis type="number" stroke={THEME_COLORS.muted} />
                          <YAxis dataKey="name" type="category" width={150} stroke={THEME_COLORS.muted} />
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
                    <ResponsiveContainer width="100%" height={240}>
                      <BarChart data={themeList.slice(0, 12)} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                        <XAxis type="number" stroke={THEME_COLORS.muted} />
                        <YAxis dataKey="name" type="category" width={170} stroke={THEME_COLORS.muted} />
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
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={bodyLocationMix} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                          <XAxis type="number" stroke={THEME_COLORS.muted} />
                          <YAxis
                            dataKey="location"
                            type="category"
                            width={130}
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
                      <ResponsiveContainer width="100%" height={220}>
                        <BarChart data={bodySignalList.slice(0, 12)} layout="vertical">
                          <CartesianGrid strokeDasharray="3 3" stroke={THEME_COLORS.mutedBorder} />
                          <XAxis type="number" stroke={THEME_COLORS.muted} />
                          <YAxis dataKey="name" type="category" width={160} stroke={THEME_COLORS.muted} />
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
            className={activeTab === "ask" ? "active" : ""}
            onClick={() => setActiveTab("ask")}
          >
            talk
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
                  setComposerVariant("prompt");
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
                  setComposerVariant("fresh");
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
                {composerVariant === "fresh" ? (
                  <input
                    className="reflect-fresh-input"
                    value={reflectionText}
                    placeholder="ask about yourself"
                    onChange={(event) => setReflectionText(event.target.value)}
                    onKeyDown={onReflectionComposerKeyDown}
                  />
                ) : (
                  <textarea
                    className="reflect-textarea"
                    rows={8}
                    value={reflectionText}
                    placeholder='Try writing in your own words: "What happened? What did I feel in my body? Where did I get reactive or calm?"'
                    onChange={(event) => setReflectionText(event.target.value)}
                    onKeyDown={onReflectionComposerKeyDown}
                  />
                )}
                <div className="toolbar reflect-submit-wrap">
                  <button
                    type="button"
                    className={`reflect-submit-button ${composerVariant === "fresh" ? "reflect-submit-button-compact" : ""}`.trim()}
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

        {activeTab === "ask" ? (
          <section className={`card chat-card ${hasChatHistory ? "chat-card-active" : "chat-card-empty"}`}>
            <h2>Talk to Your Graph</h2>
            {!hasChatHistory ? <p className="talk-empty-hint">Start with one question about yourself.</p> : null}
            {hasChatHistory ? (
              <div className="chat-log">
                {chatMessages.map((message, index) => (
                  <div key={`${message.role}-${index}`} className={`chat-line ${message.role}`}>
                    <strong>{message.role === "user" ? "You" : "synapse"}:</strong>
                    {message.role === "user" ? (
                      <span> {message.content}</span>
                    ) : (
                      <Markdown>{message.content}</Markdown>
                    )}
                  </div>
                ))}
                {chatBusy ? <p className="muted">Assistant is thinking...</p> : null}
              </div>
            ) : null}
            <div className={`chat-inputs ${hasChatHistory ? "" : "chat-inputs-center"}`.trim()}>
              <input
                className="chat-input-field"
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !chatBusy) {
                    sendChat();
                  }
                }}
                placeholder="ask about yourself"
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
