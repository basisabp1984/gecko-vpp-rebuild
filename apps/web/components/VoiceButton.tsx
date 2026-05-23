"use client";

import { Mic } from "lucide-react";
import { useEffect, useState } from "react";
import clsx from "clsx";
import { getAgentChatBridge } from "./AgentChat";

interface WindowWithSpeech extends Window {
  SpeechRecognition?: unknown;
  webkitSpeechRecognition?: unknown;
}

export function VoiceButton() {
  const [pressed, setPressed] = useState(false);
  const [available, setAvailable] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const w = window as WindowWithSpeech;
    setAvailable(Boolean(w.SpeechRecognition ?? w.webkitSpeechRecognition));
  }, []);

  const handleClick = () => {
    if (!available) return;
    const bridge = getAgentChatBridge();
    if (bridge) {
      bridge.openWithVoice();
    }
  };

  const title = available
    ? "Натисніть, щоб поставити запит голосом"
    : "Голос не доступний у вашому браузері (підтримуються Chrome/Edge)";

  return (
    <button
      type="button"
      onClick={handleClick}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      disabled={!available}
      aria-label={title}
      title={title}
      className={clsx(
        "p-2 rounded-lg border transition-colors",
        !available && "opacity-50 cursor-not-allowed",
        available && pressed
          ? "bg-accent border-accent text-text-inverse"
          : "bg-bg-card border-border hover:border-accent text-text-body",
      )}
    >
      <Mic size={16} />
    </button>
  );
}
