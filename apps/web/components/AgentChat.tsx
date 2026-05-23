"use client";

import {
  Activity,
  BatteryCharging,
  Bot,
  Lightbulb,
  Mic,
  MicOff,
  Send,
  Sparkles,
  TrendingUp,
  X,
  type LucideIcon,
} from "lucide-react";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";
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

export const PERSONA_ICONS: Record<PersonaCode, LucideIcon> = {
  dispatcher_analyst: Activity,
  market_analyst: TrendingUp,
  energy_advisor: Lightbulb,
  battery_coach: BatteryCharging,
};

export interface PersonaCopy {
  display: string;
  short: string;
  tagline: string;
  icon: LucideIcon;
  samples: string[];
}

export function usePersonaCopy(code: PersonaCode): PersonaCopy {
  const t = useTranslations("personas");
  return {
    display: t(`${code}.display`),
    short: t(`${code}.short`),
    tagline: t(`${code}.tagline`),
    icon: PERSONA_ICONS[code],
    samples: t.raw(`${code}.samples`) as string[],
  };
}

export const PERSONA_ORDER: PersonaCode[] = [
  "dispatcher_analyst",
  "market_analyst",
  "energy_advisor",
  "battery_coach",
];

export type { PersonaCode };

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
  openWithPersona: (p: PersonaCode, prefill?: string) => void;
  open: () => void;
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

  const tChatErr = useTranslations("agentChat");

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
          e instanceof Error ? e.message : tChatErr("errorUnknown");
        setMessages((prev) => [
          ...prev,
          {
            id: `e-${Date.now()}`,
            role: "agent",
            text: `${tChatErr("errorPrefix")} ${errText}`,
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

  const openWithPersona = useCallback(
    (p: PersonaCode, prefill?: string) => {
      setPersona(p);
      setMessages([]);
      setOpen(true);
      if (prefill) {
        setInput(prefill);
      }
    },
    [],
  );

  const justOpen = useCallback(() => {
    setOpen(true);
  }, []);

  // Expose bridge for VoiceButton and homepage showcase.
  useEffect(() => {
    _bridge = {
      openWithVoice,
      openWithPersona,
      open: justOpen,
    };
    return () => {
      _bridge = null;
    };
  }, [openWithVoice, openWithPersona, justOpen]);

  const personaCfg = usePersonaCopy(persona);
  const PersonaIcon = personaCfg.icon;
  const tShow = useTranslations("agentShowcase");
  const tChat = useTranslations("agentChat");
  const tPersonas = useTranslations("personas");

  const askLabel = `${tShow("askButton")} · ${personaCfg.display}`;

  return (
    <>
      {/* Floating Action Button — visible on every page */}
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label={askLabel}
          title={askLabel}
          className="fixed bottom-5 right-5 z-40 group inline-flex items-center gap-2 pl-3 pr-4 py-3 rounded-full text-text-inverse bg-accent hover:bg-accent-deep shadow-elevated transition-all hover:scale-[1.03] active:scale-[0.98] sm:gap-2.5 sm:py-3.5 sm:pl-3.5 sm:pr-5 agent-fab-pulse"
        >
          <span className="relative inline-flex items-center justify-center w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-white/15">
            <PersonaIcon size={16} className="sm:hidden" />
            <PersonaIcon size={18} className="hidden sm:inline" />
            <Sparkles
              size={9}
              className="absolute -top-0.5 -right-0.5 text-white/90"
              aria-hidden
            />
          </span>
          <span className="hidden sm:inline text-sm font-semibold tracking-tight">
            {tShow("askButton")}
          </span>
          <span className="sr-only sm:hidden">{tShow("askButton")}</span>
        </button>
      )}

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
          aria-label={tChat("drawerTitle")}
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
                  aria-label={tChat("selectAgentLabel")}
                >
                  {PERSONA_ORDER.map((code) => (
                    <option key={code} value={code}>
                      {tPersonas(`${code}.display`)}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="p-1 rounded hover:bg-bg-subtle text-text-muted"
              aria-label="Close"
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
                  {tChat("emptyPrompt")}
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
                {tChat("sending")}
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
                aria-label={listening ? tChat("voiceStop") : tChat("voiceStart")}
                title={listening ? tChat("voiceStop") : tChat("voiceStart")}
              >
                {listening ? <MicOff size={14} /> : <Mic size={14} />}
              </button>
            ) : (
              <span
                className="p-2 rounded-lg border border-border text-text-muted opacity-50"
                title={tChat("voiceUnavailable")}
              >
                <Mic size={14} />
              </span>
            )}
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={tChat("placeholder")}
              rows={1}
              className="flex-1 px-3 py-2 rounded-lg border border-border bg-bg-page text-text-body resize-none focus:outline-none focus:border-accent text-sm"
              disabled={busy}
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="p-2 rounded-lg bg-accent text-text-inverse hover:bg-accent-deep transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label={tChat("submit")}
            >
              <Send size={14} />
            </button>
          </form>
        </aside>
      </div>
    </>
  );
}
