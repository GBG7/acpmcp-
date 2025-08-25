import { useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";
import { nanoid } from "nanoid";

import { ChatInput } from "@/components/custom/chatinput";
import { PreviewMessage, ThinkingMessage } from "@/components/custom/message";
import { useScrollToBottom } from "@/components/custom/use-scroll-to-bottom";
import { Overview } from "@/components/custom/overview";
import { Header } from "@/components/custom/header";

import { message } from "@/interfaces/interfaces";

export function Chat() {
  const [messagesContainerRef, messagesEndRef] =
    useScrollToBottom<HTMLDivElement>();

  const [messages, setMessages] = useState<message[]>([]);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // hold WS + handler so we can cleanly reattach
  const wsRef = useRef<WebSocket | null>(null);
  const handlerRef = useRef<((e: MessageEvent) => void) | null>(null);

  // --- Build a dynamic WS URL ---
  // Preferred: allow build-time override with Vite env
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const HOST =
    (import.meta as any).env?.VITE_WS_HOST ?? window.location.hostname;
  const PORT = (import.meta as any).env?.VITE_WS_PORT ?? "8090";
  const WS_URL =
    (import.meta as any).env?.VITE_WS_URL ?? `${proto}://${HOST}:${PORT}`;

  // --- Create the socket on mount ---
  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.addEventListener("open", () => {
      console.log("[WS] open →", WS_URL);
    });
    ws.addEventListener("close", (e) => {
      console.log("[WS] close", e.code, e.reason);
    });
    ws.addEventListener("error", (e) => {
      console.log("[WS] error", e);
    });

    // cleanup on unmount or URL change
    return () => {
      if (handlerRef.current) ws.removeEventListener("message", handlerRef.current);
      ws.close();
      wsRef.current = null;
      handlerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [WS_URL]);

  // ---- helper: detach last handler
  const cleanupMessageHandler = () => {
    const ws = wsRef.current;
    if (ws && handlerRef.current) {
      ws.removeEventListener("message", handlerRef.current);
      handlerRef.current = null;
    }
  };

  // ----------------------
  // Send user question
  async function handleSubmit(text?: string) {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || isLoading) return;

    const userText = text || question;
    const traceId = uuidv4();

    setIsLoading(true);
    setMessages((prev) => [...prev, { id: traceId, role: "user", content: userText }]);
    setQuestion("");
    cleanupMessageHandler();

    ws.send(userText);

    // ---- New message handler ----
    const handler = (event: MessageEvent) => {
      // the backend sends JSON payloads and "[END]"
      if (event.data === "[END]") {
        setIsLoading(false);
        return;
      }

      const raw = typeof event.data === "string" ? event.data : String(event.data);
      const chunks = raw.trim().startsWith("{")
        ? raw.replace(/}\s*{/g, "}\n{").split("\n")
        : [raw];

      for (const piece of chunks) {
        let payload: any = null;
        try {
          payload = JSON.parse(piece);
        } catch {
          /* not JSON → treat as text */
        }

        // IMAGE branch
        if (payload?.type === "image" && payload.data) {
          setMessages((prev) => [
            ...prev,
            { id: nanoid(), role: "assistant", imgSrc: payload.data },
          ]);
          continue;
        }

        // TEXT branch
        const assistantText = payload?.data ?? piece;
        setMessages((prev) => {
          const last = prev.at(-1);
          const merged =
            last?.role === "assistant"
              ? (last.content ?? "") + assistantText
              : assistantText;

          const assistantMsg: message = {
            id: uuidv4(),
            role: "assistant",
            content: merged,
          };

          return last?.role === "assistant"
            ? [...prev.slice(0, -1), assistantMsg]
            : [...prev, assistantMsg];
        });
      }
    };

    handlerRef.current = handler;
    ws.addEventListener("message", handler);
  }

  return (
    <div className="flex flex-col min-w-0 h-dvh bg-background">
      <Header />

      <div
        className="flex flex-col min-w-0 gap-6 flex-1 overflow-y-scroll pt-4"
        ref={messagesContainerRef}
      >
        {messages.length === 0 && <Overview />}

        {messages.map((m, i) => (
          <PreviewMessage key={i} message={m} />
        ))}

        {isLoading && <ThinkingMessage />}

        <div ref={messagesEndRef} className="shrink-0 min-w-[24px] min-h-[24px]" />
      </div>

      <div className="flex mx-auto px-4 bg-background pb-4 md:pb-6 gap-2 w-full md:max-w-3xl">
        <ChatInput
          question={question}
          setQuestion={setQuestion}
          onSubmit={handleSubmit}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}
