"use client";

import { Bot, Mic, MicOff, Send, Sparkles, X } from "lucide-react";
import { usePathname } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import clsx from "clsx";
import { fetchAPI } from "@/lib/api";

/* -------------------------------------------------------------------------- */
/* Types                                                                       */
/* -------------------------------------------------------------------------- */

type PersonaCode =
  | "dispatcher_analyst"
  | "market_analyst"
  | "energy_advisor"
  | "battery_coach";

interface AgentQueryResponse {
  answer: string;
  intent: string;
  confidence: number;
  evidence: EvidenceChip[];
  persona: string;
  duration_ms: number;
}

interface EvidenceChip {
  table?: string;
  row_id?: string;
  columns_used?: string[];
  ui_link?: string;
  label?: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "agent";
  text: string;
  intent?: string;
  confidence?: number;
  evidence?: EvidenceChip[];
  durationMs?: number;
}

const PERSONA_META: Record<
  PersonaCode,
  {
    display: string;
    samples: string[];
  }
> = {
  dispatcher_analyst: {
    display: "Диспетчерський аналітик",
    samples: [
      "що сьогодні з виробництвом?",
      "поясни небаланс",
      "коли наступне ТО?",
    ],
  },
  market_analyst: {
    display: "Ринковий аналітик",
    samples: [
      "який бід на завтра?",
      "розбий виторг по каналах",
      "коли арбітражне вікно?",
    ],
  },
  energy_advisor: {
    display: "Енергетичний радник",
    samples: [
      "скільки спожили своєї генерації?",
      "сценарій блекауту",
      "вплив тарифу на оплату",
    ],
  },
  battery_coach: {
    display: "Тренер по батареях",
    samples: [
      "коли заряджати батарею?",
      "який поточний SOC?",
      "перевір цикли батареї",
    ],
  },
};

/* -------------------------------------------------------------------------- */
/* URL → persona resolution                                                    */
/* -------------------------------------------------------------------------- */

function resolvePersonaFromPath(path: string): PersonaCode {
  if (path.startsWith("/producer")) return "dispatcher_analyst";
  if (path.startsWith("/c-i")) return "energy_advisor";
  if (path.startsWith("/storage")) return "battery_coach";
  return "market_analyst";
}

/* -------------------------------------------------------------------------- */
/* Browser speech APIs                                                         */
/* -------------------------------------------------------------------------- */

interface BrowserSpeechRecognition {
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechResultLike) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  lang: string;
  continuous: boolean;
  interimResults: boolean;
}

interface SpeechResultLike {
  results: ArrayLike<{
    isFinal: boolean;
    0: { transcript: string };
  }>;
  resultIndex: number;
}

interface WindowWithSpeech extends Window {
  SpeechRecognition?: new () => BrowserSpeechRecognition;
  webkitSpeechRecognition?: new () => BrowserSpeechRecognition;
}

function getSpeechRecognitionCtor():
  | (new () => BrowserSpeechRecognition)
  | null {
  if (typeof window === "undefined") return null;
  const w = window as WindowWithSpeech;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

function speakUkrainian(text: string) {
  if (typeof window === "undefined") return;
  if (!("speechSynthesis" in window)) return;
  try {
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "uk-UA";
    utter.rate = 1.05;
    utter.pitch = 1.0;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
  } catch {
    // Browser-specific TTS error — silently ignore.
  }
}

/* -------------------------------------------------------------------------- */
/* Singleton helper to bridge VoiceButton → AgentChat                          */
/* -------------------------------------------------------------------------- */

interface AgentChatBridge {
  openWithVoice: () => void;
}

let _bridge: AgentChatBridge | null = null;

export function getAgentChatBridge(): AgentChatBridge | null {
  return _bridge;
}

/* -------------------------------------------------------------------------- */
/* AgentChat component                                                         */
/* -------------------------------------------------------------------------- */

export function AgentChat() {
  const pathname = usePathname() ?? "/";
  const autoPersona = useMemo(() => resolvePersonaFromPath(pathname), [pathname]);

  const [open, setOpen] = useState(false);
  const [persona, setPersona] = useState<PersonaCode>(autoPersona);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceAvailable, setVoiceAvailable] = useState(false);

  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const listEndRef = useRef<HTMLDivElement | null>(null);

  // Sync persona when URL changes — but don't fight a manual override
  // mid-conversation (only sync on open).
  useEffect(() => {
    if (open) return;
    setPersona(autoPersona);
  }, [autoPersona, open]);

  // Detect Web Speech availability.
  useEffect(() => {
    setVoiceAvailable(getSpeechRecognitionCtor() !== null);
  }, []);

  // Scroll to bottom on new message.
  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Body scroll lock when drawer open.
  useEffect(() => {
    if (!open) return;
    const orig = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = orig;
    };
  }, [open]);

  const sendQuery = useCallback(
    async (question: string, opts: { speakAnswer?: boolean } = {}) => {
      const trimmed = question.trim();
      if (!trimmed || busy) return;
      const userMsg: ChatMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        text: trimmed,
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setBusy(true);
      try {
        const res = await fetchAPI<AgentQueryResponse>(
          `/api/v1/agents/${persona}/query`,
          { method: "POST", body: { question: trimmed } },
        );
        const r = res.data;
        const agentMsg: ChatMessage = {
          id: `a-${Date.now()}`,
          role: "agent",
          text: r.answer,
          intent: r.intent,
          confidence: r.confidence,
          evidence: r.evidence,
          durationMs: r.duration_ms,
        };
        setMessages((prev) => [...prev, agentMsg]);
        if (opts.speakAnswer) speakUkrainian(r.answer);
      } catch (e: unknown) {
        const errText =
          e instanceof Error ? e.message : "Невідома помилка зв'язку з агентом";
        setMessages((prev) => [
          ...prev,
          {
            id: `e-${Date.now()}`,
            role: "agent",
            text: `[помилка] ${errText}`,
          },
        ]);
      } finally {
        setBusy(false);
      }
    },
    [busy, persona],
  );

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      void sendQuery(input);
    },
    [input, sendQuery],
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        void sendQuery(input);
      }
    },
    [input, sendQuery],
  );

  const startListening = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) return;
    try {
      const rec = new Ctor();
      rec.lang = "uk-UA";
      rec.interimResults = false;
      rec.continuous = false;
      rec.onresult = (ev: SpeechResultLike) => {
        const transcript = Array.from({ length: ev.results.length })
          .map((_, i) => ev.results[i][0].transcript)
          .join(" ")
          .trim();
        if (transcript) {
          setInput(transcript);
          void sendQuery(transcript, { speakAnswer: true });
        }
      };
      rec.onend = () => setListening(false);
      rec.onerror = () => setListening(false);
      recognitionRef.current = rec;
      rec.start();
      setListening(true);
    } catch {
      setListening(false);
    }
  }, [sendQuery]);

  const stopListening = useCallback(() => {
    try {
      recognitionRef.current?.stop();
    } catch {
      // ignore
    }
    setListening(false);
  }, []);

  const openWithVoice = useCallback(() => {
    setOpen(true);
    setTimeout(() => {
      startListening();
    }, 50);
  }, [startListening]);

  // Expose bridge for VoiceButton.
  useEffect(() => {
    _bridge = { openWithVoice };
    return () => {
      _bridge = null;
    };
  }, [openWithVoice]);

  const personaCfg = PERSONA_META[persona];

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Агент-асистент"
        title="Агент-асистент"
        className="p-2 rounded-lg border border-border bg-bg-card hover:border-accent transition-colors text-text-body"
      >
        <Bot size={16} />
      </button>

      {/* Overlay + drawer */}
      <div
        className={clsx(
          "fixed inset-0 z-50 transition-opacity",
          open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none",
        )}
        aria-hidden={!open}
      >
        <div
          className="absolute inset-0 bg-black/40"
          onClick={() => setOpen(false)}
        />
        <aside
          className={clsx(
            "absolute right-0 top-0 h-full w-full max-w-md bg-bg-card border-l border-border shadow-elevated flex flex-col transition-transform",
            open ? "translate-x-0" : "translate-x-full",
          )}
          role="dialog"
          aria-label="GECKO агент"
        >
          {/* Header */}
          <div className="p-4 border-b border-border flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <Bot size={18} className="text-accent flex-shrink-0" />
              <div className="min-w-0">
                <div className="text-sm font-semibold text-text-heading truncate">
                  {personaCfg.display}
                </div>
                <select
                  value={persona}
                  onChange={(e) => {
                    setPersona(e.target.value as PersonaCode);
                    setMessages([]);
                  }}
                  className="text-xs text-text-muted bg-transparent border border-border rounded px-1 py-0.5 mt-0.5"
                  aria-label="Обрати агента"
                >
                  <option value="dispatcher_analyst">Диспетчерський аналітик</option>
                  <option value="market_analyst">Ринковий аналітик</option>
                  <option value="energy_advisor">Енергетичний радник</option>
                  <option value="battery_coach">Тренер по батареях</option>
                </select>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="p-1 rounded hover:bg-bg-subtle text-text-muted"
              aria-label="Закрити"
            >
              <X size={18} />
            </button>
          </div>

          {/* Message list */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-sm text-text-muted">
                <p className="mb-2 flex items-center gap-1.5">
                  <Sparkles size={14} className="text-accent" />
                  Я допоможу з аналітикою на основі реальних даних. Приклади:
                </p>
                <div className="space-y-1.5">
                  {personaCfg.samples.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => setInput(q)}
                      className="block w-full text-left px-3 py-2 rounded-lg border border-border bg-bg-page hover:border-accent text-text-body text-sm"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) => (
              <div
                key={m.id}
                className={clsx(
                  "rounded-lg px-3 py-2 text-sm whitespace-pre-wrap",
                  m.role === "user"
                    ? "bg-accent-subtle text-accent-deep ml-8"
                    : "bg-bg-page border border-border text-text-body mr-8",
                )}
              >
                <div>{m.text}</div>
                {m.role === "agent" && m.intent && (
                  <div className="mt-2 flex flex-wrap items-center gap-1 text-xs">
                    <span className="px-1.5 py-0.5 rounded bg-bg-subtle text-text-muted">
                      {m.intent}
                    </span>
                    {typeof m.confidence === "number" && (
                      <span className="px-1.5 py-0.5 rounded bg-bg-subtle text-text-muted">
                        conf {(m.confidence * 100).toFixed(0)}%
                      </span>
                    )}
                    {typeof m.durationMs === "number" && (
                      <span className="px-1.5 py-0.5 rounded bg-bg-subtle text-text-muted">
                        {m.durationMs}ms
                      </span>
                    )}
                  </div>
                )}
                {m.role === "agent" && m.evidence && m.evidence.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {m.evidence.map((ev, i) => {
                      const label =
                        ev.label ??
                        (ev.table ? `Дані: ${ev.table}` : `Джерело #${i + 1}`);
                      if (ev.ui_link) {
                        return (
                          <a
                            key={i}
                            href={ev.ui_link}
                            className="text-xs px-2 py-1 rounded border border-accent/40 text-accent-deep hover:bg-accent-subtle transition-colors"
                          >
                            {label}
                          </a>
                        );
                      }
                      return (
                        <span
                          key={i}
                          className="text-xs px-2 py-1 rounded border border-border text-text-muted"
                          title={ev.columns_used?.join(", ")}
                        >
                          {label}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}

            {busy && (
              <div className="text-xs text-text-muted italic px-3 py-2">
                Агент аналізує...
              </div>
            )}
            <div ref={listEndRef} />
          </div>

          {/* Input bar */}
          <form
            onSubmit={handleSubmit}
            className="border-t border-border p-3 flex items-end gap-2"
          >
            {voiceAvailable ? (
              <button
                type="button"
                onClick={listening ? stopListening : startListening}
                className={clsx(
                  "p-2 rounded-lg border transition-colors",
                  listening
                    ? "bg-accent border-accent text-text-inverse"
                    : "bg-bg-card border-border hover:border-accent text-text-body",
                )}
                aria-label={listening ? "Зупинити запис" : "Голосовий ввід"}
                title={listening ? "Зупинити" : "Сказати голосом"}
              >
                {listening ? <MicOff size={14} /> : <Mic size={14} />}
              </button>
            ) : (
              <span
                className="p-2 rounded-lg border border-border text-text-muted opacity-50"
                title="Голос не доступний у вашому браузері"
              >
                <Mic size={14} />
              </span>
            )}
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Поставте питання..."
              rows={1}
              className="flex-1 px-3 py-2 rounded-lg border border-border bg-bg-page text-text-body resize-none focus:outline-none focus:border-accent text-sm"
              disabled={busy}
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="p-2 rounded-lg bg-accent text-text-inverse hover:bg-accent-deep transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Надіслати"
            >
              <Send size={14} />
            </button>
          </form>
        </aside>
      </div>
    </>
  );
}
