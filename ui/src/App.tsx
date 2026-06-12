import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import {
  Send,
  Database,
  FileText,
  Server,
  ChevronDown,
  ChevronRight,
  Activity,
  Dumbbell,
  Zap,
  Heart,
  Loader2,
  Sparkles,
  GitBranch,
  Search,
  Brain,
  Layers,
  MessageSquare,
  Check,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────

interface Source {
  source: string;
  type: string;
  confidence: number;
  summary: string;
  row_count: number;
}

interface Pipeline {
  domains: string[];
  catalog_candidates: number;
  selected_sources: string[];
  kg_expanded: string[];
  total_queried: number;
}

interface QueryResult {
  question: string;
  answer: string;
  sources_consulted: Source[];
  pipeline: Pipeline;
}

type StageStatus = "pending" | "active" | "done";

interface StageState {
  domain_classification: { status: StageStatus; domains?: string[] };
  catalog_search: { status: StageStatus; candidates?: number };
  reranking: { status: StageStatus; selected?: string[] };
  kg_expansion: { status: StageStatus; added?: string[] };
  tool_execution: { status: StageStatus; total?: number };
  synthesizing: { status: StageStatus };
}

interface StreamingState {
  stages: StageState;
  sources: Source[];
  tokens: string;
  pipeline: Pipeline | null;
  done: boolean;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  result?: QueryResult;
  streaming?: StreamingState;
  timestamp: Date;
}

// ── Helpers ────────────────────────────────────────────────────

const INITIAL_STAGES: StageState = {
  domain_classification: { status: "pending" },
  catalog_search: { status: "pending" },
  reranking: { status: "pending" },
  kg_expansion: { status: "pending" },
  tool_execution: { status: "pending" },
  synthesizing: { status: "pending" },
};

const sourceIcon = (type: string) => {
  switch (type) {
    case "sql":
      return <Database className="w-4 h-4" />;
    case "nosql":
      return <Server className="w-4 h-4" />;
    case "pdf":
      return <FileText className="w-4 h-4" />;
    default:
      return <Database className="w-4 h-4" />;
  }
};

const sourceColor = (type: string) => {
  switch (type) {
    case "sql":
      return "from-blue-500/20 to-blue-600/10 border-blue-500/30 text-blue-400";
    case "nosql":
      return "from-emerald-500/20 to-emerald-600/10 border-emerald-500/30 text-emerald-400";
    case "pdf":
      return "from-amber-500/20 to-amber-600/10 border-amber-500/30 text-amber-400";
    default:
      return "from-gray-500/20 to-gray-600/10 border-gray-500/30 text-gray-400";
  }
};

const confidenceBar = (confidence: number) => {
  const pct = Math.round(confidence * 100);
  const color =
    pct >= 80
      ? "bg-emerald-500"
      : pct >= 50
        ? "bg-amber-500"
        : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-gray-400 tabular-nums w-8">{pct}%</span>
    </div>
  );
};

// ── Components ─────────────────────────────────────────────────

const STAGE_META: Record<
  string,
  { icon: React.ReactNode; label: string; color: string }
> = {
  domain_classification: {
    icon: <Search className="w-3.5 h-3.5" />,
    label: "Classifying domains",
    color: "text-violet-400",
  },
  catalog_search: {
    icon: <Layers className="w-3.5 h-3.5" />,
    label: "Searching catalog",
    color: "text-blue-400",
  },
  reranking: {
    icon: <Sparkles className="w-3.5 h-3.5" />,
    label: "Reranking sources",
    color: "text-amber-400",
  },
  kg_expansion: {
    icon: <GitBranch className="w-3.5 h-3.5" />,
    label: "Expanding via KG",
    color: "text-emerald-400",
  },
  tool_execution: {
    icon: <Zap className="w-3.5 h-3.5" />,
    label: "Querying tools",
    color: "text-rose-400",
  },
  synthesizing: {
    icon: <Brain className="w-3.5 h-3.5" />,
    label: "Synthesizing",
    color: "text-indigo-400",
  },
};

function LivePipelineStages({ stages }: { stages: StageState }) {
  const stageOrder = [
    "domain_classification",
    "catalog_search",
    "reranking",
    "kg_expansion",
    "tool_execution",
    "synthesizing",
  ] as const;

  const getDetail = (key: string): string => {
    const s = stages[key as keyof StageState] as Record<string, unknown>;
    switch (key) {
      case "domain_classification":
        return s.domains ? (s.domains as string[]).join(", ") : "";
      case "catalog_search":
        return s.candidates != null ? `${s.candidates} candidates` : "";
      case "reranking":
        return s.selected ? `${(s.selected as string[]).length} selected` : "";
      case "kg_expansion": {
        const added = s.added as string[] | undefined;
        return added?.length ? `+${added.length} sources` : "none added";
      }
      case "tool_execution":
        return s.total != null ? `${s.total} sources` : "";
      default:
        return "";
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-1 mb-3">
      {stageOrder.map((key, i) => {
        const meta = STAGE_META[key];
        const stage = stages[key];
        const detail = getDetail(key);
        const isPending = stage.status === "pending";
        const isActive = stage.status === "active";
        const isDone = stage.status === "done";

        return (
          <div key={key} className="flex items-center gap-1">
            <div
              className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs transition-all duration-300 ${
                isPending
                  ? "bg-gray-800/40 border border-gray-800/50 opacity-40"
                  : isActive
                    ? "bg-gray-800/80 border border-gray-600/50 ring-1 ring-violet-500/30"
                    : "bg-gray-800/80 border border-gray-700/50"
              }`}
            >
              <span className={isDone ? "text-emerald-400" : meta.color}>
                {isDone ? <Check className="w-3.5 h-3.5" /> : isActive ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : meta.icon}
              </span>
              <span className={isPending ? "text-gray-600" : "text-gray-400"}>
                {meta.label}
              </span>
              {detail && isDone && (
                <>
                  <span className="text-gray-600">·</span>
                  <span className="text-gray-300">{detail}</span>
                </>
              )}
            </div>
            {i < stageOrder.length - 1 && (
              <ChevronRight className="w-3 h-3 text-gray-700" />
            )}
          </div>
        );
      })}
    </div>
  );
}

function PipelineStages({ pipeline }: { pipeline: Pipeline }) {
  const stages = [
    {
      icon: <Search className="w-3.5 h-3.5" />,
      label: "Domain Classification",
      detail: pipeline.domains.join(", "),
      color: "text-violet-400",
    },
    {
      icon: <Layers className="w-3.5 h-3.5" />,
      label: "Catalog Search",
      detail: `${pipeline.catalog_candidates} candidates`,
      color: "text-blue-400",
    },
    {
      icon: <Sparkles className="w-3.5 h-3.5" />,
      label: "LLM Reranking",
      detail: `${pipeline.selected_sources.length} selected`,
      color: "text-amber-400",
    },
    {
      icon: <GitBranch className="w-3.5 h-3.5" />,
      label: "KG Expansion",
      detail:
        pipeline.kg_expanded.length > 0
          ? `+${pipeline.kg_expanded.join(", +")}`
          : "no expansion needed",
      color: "text-emerald-400",
    },
    {
      icon: <Zap className="w-3.5 h-3.5" />,
      label: "Tool Execution",
      detail: `${pipeline.total_queried} sources queried`,
      color: "text-rose-400",
    },
  ];

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {stages.map((stage, i) => (
        <div key={i} className="flex items-center gap-1">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-gray-800/80 border border-gray-700/50 text-xs">
            <span className={stage.color}>{stage.icon}</span>
            <span className="text-gray-400">{stage.label}</span>
            <span className="text-gray-500">·</span>
            <span className="text-gray-300">{stage.detail}</span>
          </div>
          {i < stages.length - 1 && (
            <ChevronRight className="w-3 h-3 text-gray-600" />
          )}
        </div>
      ))}
    </div>
  );
}

function SourceCard({ source }: { source: Source }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`rounded-lg border bg-gradient-to-br ${sourceColor(source.type)} backdrop-blur-sm overflow-hidden animate-fade-in-up`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {sourceIcon(source.type)}
          <span className="text-sm font-medium text-gray-200 truncate">
            {source.source}
          </span>
          <span className="px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-black/20 rounded">
            {source.type}
          </span>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <span className="text-xs text-gray-400">
            {source.row_count} results
          </span>
          <div className="w-20">{confidenceBar(source.confidence)}</div>
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
        </div>
      </button>
      {expanded && (
        <div className="px-3 pb-3 border-t border-white/5">
          <p className="text-xs text-gray-400 mt-2 leading-relaxed max-h-32 overflow-y-auto scrollbar-thin">
            {source.summary.length > 500
              ? source.summary.slice(0, 500) + "..."
              : source.summary}
          </p>
        </div>
      )}
    </div>
  );
}

function AssistantMessage({ message }: { message: Message }) {
  const [showPipeline, setShowPipeline] = useState(false);
  const result = message.result;
  const streaming = message.streaming;
  const isStreaming = streaming && !streaming.done;

  const content = result ? result.answer : streaming ? streaming.tokens : message.content;
  const sources = result ? result.sources_consulted : streaming ? streaming.sources : [];
  const pipeline = result?.pipeline ?? streaming?.pipeline ?? null;

  return (
    <div className="animate-fade-in-up">
      <div className="flex items-start gap-3 px-5 py-4">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Brain className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1 min-w-0 space-y-3">
          {/* Live pipeline stages while streaming */}
          {streaming && (
            <LivePipelineStages stages={streaming.stages} />
          )}

          {/* Sources as they arrive */}
          {sources.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {sources.map((src, i) => (
                <SourceCard key={i} source={src} />
              ))}
            </div>
          )}

          {/* Answer text (streaming or final) */}
          {content && (
            <div className="prose prose-invert prose-sm max-w-none text-gray-200 leading-relaxed">
              <ReactMarkdown>{content + (isStreaming && streaming.tokens ? "▍" : "")}</ReactMarkdown>
            </div>
          )}

          {/* Completed pipeline toggle (only after stream finishes) */}
          {!streaming && result && (
            <div className="space-y-2">
              <button
                onClick={() => setShowPipeline(!showPipeline)}
                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                {showPipeline ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" />
                )}
                Pipeline stages
              </button>
              {showPipeline && <PipelineStages pipeline={result.pipeline} />}
            </div>
          )}

          {/* Pipeline toggle after streaming done */}
          {streaming?.done && pipeline && (
            <div className="space-y-2">
              <button
                onClick={() => setShowPipeline(!showPipeline)}
                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                {showPipeline ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" />
                )}
                Pipeline details
              </button>
              {showPipeline && <PipelineStages pipeline={pipeline} />}
            </div>
          )}

          <span className="text-[10px] text-gray-600">
            {message.timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
      </div>
    </div>
  );
}

function UserMessage({ message }: { message: Message }) {
  return (
    <div className="animate-fade-in-up">
      <div className="flex items-start gap-3 px-5 py-4 justify-end">
        <div className="max-w-[75%] space-y-1">
          <div className="bg-gradient-to-br from-violet-600 to-indigo-600 rounded-2xl rounded-br-md px-4 py-2.5 text-sm text-white">
            {message.content}
          </div>
          <div className="text-right">
            <span className="text-[10px] text-gray-600">
              {message.timestamp.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function SuggestedQueries({ onSelect }: { onSelect: (q: string) => void }) {
  const queries = [
    "Which members are losing the most weight?",
    "What are the most popular classes?",
    "Which trainers have low ratings and why?",
    "What is the recommended protein intake for muscle building?",
    "Are members following nutrition guidelines?",
    "What health risks have been identified?",
  ];

  return (
    <div className="flex flex-wrap gap-2 justify-center px-4">
      {queries.map((q, i) => (
        <button
          key={i}
          onClick={() => onSelect(q)}
          className="px-3 py-1.5 text-xs text-gray-400 bg-gray-800/60 border border-gray-700/50 rounded-full hover:bg-gray-700/60 hover:text-gray-200 hover:border-gray-600 transition-all"
        >
          {q}
        </button>
      ))}
    </div>
  );
}

// ── SSE Parser ─────────────────────────────────────────────────

function parseSSE(text: string): Array<{ event: string; data: string }> {
  const events: Array<{ event: string; data: string }> = [];
  const blocks = text.split("\n\n");
  for (const block of blocks) {
    if (!block.trim()) continue;
    let event = "message";
    let data = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event: ")) event = line.slice(7);
      else if (line.startsWith("data: ")) data = line.slice(6);
    }
    if (data) events.push({ event, data });
  }
  return events;
}

// ── Stage transition helpers ───────────────────────────────────

const STAGE_ORDER = [
  "domain_classification",
  "catalog_search",
  "reranking",
  "kg_expansion",
  "tool_execution",
  "synthesizing",
] as const;

function advanceStages(
  current: StageState,
  completedName: string,
  extras: Record<string, unknown>,
): StageState {
  const next = { ...current };
  const idx = STAGE_ORDER.indexOf(completedName as (typeof STAGE_ORDER)[number]);

  for (let i = 0; i < STAGE_ORDER.length; i++) {
    const key = STAGE_ORDER[i] as keyof StageState;
    if (i < idx) {
      next[key] = { ...next[key], status: "done" };
    } else if (i === idx) {
      next[key] = { ...next[key], ...extras, status: "done" } as StageState[typeof key];
    } else if (i === idx + 1) {
      next[key] = { ...next[key], status: "active" };
    }
  }
  return next;
}

// ── App ────────────────────────────────────────────────────────

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(scrollToBottom, [messages, loading, scrollToBottom]);

  const handleSubmit = async (question?: string) => {
    const q = question || input.trim();
    if (!q || loading) return;

    setInput("");

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: q,
      timestamp: new Date(),
    };

    const assistantId = crypto.randomUUID();
    const initialStreaming: StreamingState = {
      stages: { ...INITIAL_STAGES, domain_classification: { status: "active" } },
      sources: [],
      tokens: "",
      pipeline: null,
      done: false,
    };

    const assistantMsg: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      streaming: initialStreaming,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setLoading(true);

    try {
      const res = await fetch("/api/query/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let state = { ...initialStreaming };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lastDoubleNewline = buffer.lastIndexOf("\n\n");
        if (lastDoubleNewline === -1) continue;

        const complete = buffer.slice(0, lastDoubleNewline + 2);
        buffer = buffer.slice(lastDoubleNewline + 2);

        const events = parseSSE(complete);

        for (const evt of events) {
          try {
            const data = JSON.parse(evt.data);

            switch (evt.event) {
              case "stage": {
                const { name, ...extras } = data;
                state = {
                  ...state,
                  stages: advanceStages(state.stages, name, extras),
                };
                break;
              }
              case "source":
                state = {
                  ...state,
                  sources: [...state.sources, data as Source],
                };
                break;
              case "token":
                state = {
                  ...state,
                  tokens: state.tokens + data.text,
                };
                break;
              case "done":
                state = {
                  ...state,
                  pipeline: data.pipeline,
                  done: true,
                };
                break;
            }
          } catch {
            // skip malformed events
          }
        }

        const snapshot = { ...state };
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, streaming: snapshot } : m,
          ),
        );
      }

      // Finalize
      const finalState: StreamingState = { ...state, done: true };
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: state.tokens, streaming: finalState } : m,
        ),
      );
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: `Something went wrong: ${err instanceof Error ? err.message : "Unknown error"}. Make sure the API server is running on port 8000.`,
                streaming: undefined,
              }
            : m,
        ),
      );
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="h-full flex flex-col bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-gray-800/80 bg-gray-950/80 backdrop-blur-xl sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-5 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center">
              <Dumbbell className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-gray-100">
                Agentic RAG
              </h1>
              <p className="text-[11px] text-gray-500">
                Health & Fitness Intelligence
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gray-800/60 border border-gray-700/50">
              <Database className="w-3 h-3 text-blue-400" />
              <span className="text-[10px] text-gray-400">SQL</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gray-800/60 border border-gray-700/50">
              <Server className="w-3 h-3 text-emerald-400" />
              <span className="text-[10px] text-gray-400">NoSQL</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gray-800/60 border border-gray-700/50">
              <FileText className="w-3 h-3 text-amber-400" />
              <span className="text-[10px] text-gray-400">PDF</span>
            </div>
          </div>
        </div>
      </header>

      {/* Messages */}
      <main className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="max-w-4xl mx-auto">
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 px-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-600/20 to-indigo-600/20 border border-violet-500/20 flex items-center justify-center">
                <MessageSquare className="w-8 h-8 text-violet-400" />
              </div>
              <div className="text-center space-y-2">
                <h2 className="text-xl font-semibold text-gray-200">
                  Ask anything about your fitness data
                </h2>
                <p className="text-sm text-gray-500 max-w-md">
                  Query across member records, workout sessions, nutrition logs,
                  health assessments, and policy documents — all at once.
                </p>
              </div>
              <SuggestedQueries onSelect={(q) => handleSubmit(q)} />
            </div>
          ) : (
            <div className="py-2">
              {messages.map((msg) =>
                msg.role === "user" ? (
                  <UserMessage key={msg.id} message={msg} />
                ) : (
                  <AssistantMessage key={msg.id} message={msg} />
                ),
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </main>

      {/* Input */}
      <footer className="flex-shrink-0 border-t border-gray-800/80 bg-gray-950/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-5 py-3">
          <div className="flex items-end gap-2 bg-gray-900 border border-gray-800 rounded-2xl px-4 py-2 focus-within:border-violet-500/50 focus-within:ring-1 focus-within:ring-violet-500/20 transition-all">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about members, workouts, nutrition, health..."
              rows={1}
              className="flex-1 bg-transparent text-sm text-gray-100 placeholder-gray-600 resize-none outline-none py-1.5 max-h-32"
              style={{
                height: "auto",
                minHeight: "24px",
              }}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = "auto";
                el.style.height = Math.min(el.scrollHeight, 128) + "px";
              }}
              disabled={loading}
              autoFocus
            />
            <button
              onClick={() => handleSubmit()}
              disabled={!input.trim() || loading}
              className="p-2 rounded-xl bg-violet-600 hover:bg-violet-500 disabled:bg-gray-800 disabled:text-gray-600 text-white transition-all flex-shrink-0"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="text-center text-[10px] text-gray-700 mt-2">
            Queries across 6 SQL tables, 3 MongoDB collections, and 3 PDF
            documents via Gemini
          </p>
        </div>
      </footer>
    </div>
  );
}
