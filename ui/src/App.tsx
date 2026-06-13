import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import {
  Send,
  Database,
  FileText,
  Server,
  ChevronDown,
  ChevronRight,
  Dumbbell,
  Zap,
  Loader2,
  Brain,
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

interface AgentCall {
  tool: string;
  args: Record<string, string>;
  turn: number;
}

interface AgentResult {
  source: string;
  type: string;
  confidence: number;
  row_count: number;
  summary: string;
  attempts: number;
}

interface AgentStep {
  call: AgentCall;
  result?: AgentResult;
}

interface AgentMeta {
  sources_consulted: Source[];
  turns: number;
}

interface QueryResult {
  question: string;
  answer: string;
  sources_consulted: Source[];
  agent_trace: AgentStep[];
}

interface StreamingState {
  currentTurn: number;
  steps: AgentStep[];
  synthesizing: boolean;
  tokens: string;
  meta: AgentMeta | null;
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

const toolMeta: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  query_sql: {
    icon: <Database className="w-3.5 h-3.5" />,
    label: "SQL Agent",
    color: "text-blue-400",
  },
  query_nosql: {
    icon: <Server className="w-3.5 h-3.5" />,
    label: "NoSQL Agent",
    color: "text-emerald-400",
  },
  search_pdfs: {
    icon: <FileText className="w-3.5 h-3.5" />,
    label: "PDF Agent",
    color: "text-amber-400",
  },
};

function LiveAgentTrace({
  steps,
  currentTurn,
  synthesizing,
}: {
  steps: AgentStep[];
  currentTurn: number;
  synthesizing: boolean;
}) {
  return (
    <div className="space-y-1.5 mb-3">
      {steps.map((step, i) => {
        const meta = toolMeta[step.call.tool] || {
          icon: <Zap className="w-3.5 h-3.5" />,
          label: step.call.tool,
          color: "text-gray-400",
        };
        const hasResult = !!step.result;
        const argLabel =
          step.call.args.table_name ||
          step.call.args.collection_name ||
          step.call.args.pdf_name ||
          "";

        return (
          <div
            key={i}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs transition-all duration-300 ${
              hasResult
                ? "bg-gray-800/80 border border-gray-700/50"
                : "bg-gray-800/80 border border-gray-600/50 ring-1 ring-violet-500/30"
            }`}
          >
            <span className="text-gray-600 tabular-nums w-4">
              {step.call.turn}
            </span>
            <span className={hasResult ? "text-emerald-400" : meta.color}>
              {hasResult ? (
                <Check className="w-3.5 h-3.5" />
              ) : (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              )}
            </span>
            <span className={meta.color}>{meta.label}</span>
            {argLabel && (
              <>
                <span className="text-gray-600">·</span>
                <span className="text-gray-400">{argLabel}</span>
              </>
            )}
            {hasResult && step.result && (
              <>
                <span className="text-gray-600">·</span>
                <span className="text-gray-300">
                  {step.result.row_count} results
                </span>
                {step.result.attempts > 1 && (
                  <span className="text-amber-400">
                    (retried {step.result.attempts}x)
                  </span>
                )}
              </>
            )}
          </div>
        );
      })}
      {synthesizing && (
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs bg-gray-800/80 border border-gray-600/50 ring-1 ring-indigo-500/30">
          <span className="text-gray-600 tabular-nums w-4" />
          <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
          <span className="text-indigo-400">Synthesizing answer</span>
        </div>
      )}
      {!synthesizing && steps.length === 0 && currentTurn > 0 && (
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs bg-gray-800/80 border border-gray-600/50 ring-1 ring-violet-500/30">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-violet-400" />
          <span className="text-violet-400">
            Orchestrator reasoning (turn {currentTurn})
          </span>
        </div>
      )}
    </div>
  );
}

function AgentTraceSteps({ steps }: { steps: AgentStep[] }) {
  return (
    <div className="space-y-1">
      {steps.map((step, i) => {
        const meta = toolMeta[step.call.tool] || {
          icon: <Zap className="w-3.5 h-3.5" />,
          label: step.call.tool,
          color: "text-gray-400",
        };
        const argLabel =
          step.call.args.table_name ||
          step.call.args.collection_name ||
          step.call.args.pdf_name ||
          "";

        return (
          <div
            key={i}
            className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-gray-800/80 border border-gray-700/50 text-xs"
          >
            <span className="text-gray-600 tabular-nums w-4">
              {step.call.turn}
            </span>
            <span className={meta.color}>{meta.icon}</span>
            <span className="text-gray-400">{meta.label}</span>
            {argLabel && (
              <>
                <span className="text-gray-500">·</span>
                <span className="text-gray-300">{argLabel}</span>
              </>
            )}
            {step.result && (
              <>
                <span className="text-gray-500">·</span>
                <span className="text-gray-300">
                  {step.result.row_count} results
                </span>
                {step.result.attempts > 1 && (
                  <span className="text-amber-400">
                    (retried {step.result.attempts}x)
                  </span>
                )}
              </>
            )}
          </div>
        );
      })}
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
  const [showTrace, setShowTrace] = useState(false);
  const result = message.result;
  const streaming = message.streaming;
  const isStreaming = streaming && !streaming.done;

  const content = result
    ? result.answer
    : streaming
      ? streaming.tokens
      : message.content;

  const sources = result
    ? result.sources_consulted
    : streaming?.meta?.sources_consulted ?? [];

  const steps = result?.agent_trace ?? streaming?.steps ?? [];

  return (
    <div className="animate-fade-in-up">
      <div className="flex items-start gap-3 px-5 py-4">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Brain className="w-4 h-4 text-white" />
        </div>
        <div className="flex-1 min-w-0 space-y-3">
          {/* Live agent trace while streaming */}
          {streaming && !streaming.done && (
            <LiveAgentTrace
              steps={streaming.steps}
              currentTurn={streaming.currentTurn}
              synthesizing={streaming.synthesizing}
            />
          )}

          {/* Source cards */}
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
              <ReactMarkdown>
                {content + (isStreaming && streaming.tokens ? "▍" : "")}
              </ReactMarkdown>
            </div>
          )}

          {/* Agent trace toggle (after done) */}
          {(streaming?.done || result) && steps.length > 0 && (
            <div className="space-y-2">
              <button
                onClick={() => setShowTrace(!showTrace)}
                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                {showTrace ? (
                  <ChevronDown className="w-3.5 h-3.5" />
                ) : (
                  <ChevronRight className="w-3.5 h-3.5" />
                )}
                Agent trace ({steps.length} calls)
              </button>
              {showTrace && <AgentTraceSteps steps={steps} />}
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

// ── SSE event handlers ────────────────────────────────────────

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
      currentTurn: 0,
      steps: [],
      synthesizing: false,
      tokens: "",
      meta: null,
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
                if (data.name === "reasoning") {
                  state = { ...state, currentTurn: data.turn };
                } else if (data.name === "synthesizing") {
                  state = { ...state, synthesizing: true };
                }
                break;
              }
              case "agent_call": {
                const call: AgentCall = {
                  tool: data.tool,
                  args: data.args,
                  turn: data.turn,
                };
                state = {
                  ...state,
                  steps: [...state.steps, { call }],
                };
                break;
              }
              case "agent_result": {
                const agentResult: AgentResult = data as AgentResult;
                const updatedSteps = [...state.steps];
                let pending = -1;
                for (let i = updatedSteps.length - 1; i >= 0; i--) {
                  if (!updatedSteps[i].result) {
                    pending = i;
                    break;
                  }
                }
                if (pending >= 0) {
                  updatedSteps[pending] = {
                    ...updatedSteps[pending],
                    result: agentResult,
                  };
                }
                state = { ...state, steps: updatedSteps };
                break;
              }
              case "token":
                state = { ...state, tokens: state.tokens + data.text };
                break;
              case "done":
                state = {
                  ...state,
                  meta: {
                    sources_consulted: data.sources_consulted ?? [],
                    turns: data.turns ?? 0,
                  },
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
