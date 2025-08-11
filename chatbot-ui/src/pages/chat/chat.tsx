import { useState, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { nanoid } from "nanoid";

import { ChatInput } from "@/components/custom/chatinput";
import { PreviewMessage, ThinkingMessage } from "@/components/custom/message";
import { useScrollToBottom } from "@/components/custom/use-scroll-to-bottom";
import { Overview } from "@/components/custom/overview";
import { Header } from "@/components/custom/header";

import { message } from "@/interfaces/interfaces";

const socket = new WebSocket("ws://localhost:8090");

export function Chat() {
  const [messagesContainerRef, messagesEndRef] =
    useScrollToBottom<HTMLDivElement>();

  const [messages, setMessages] = useState<message[]>([]);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const messageHandlerRef = useRef<((e: MessageEvent) => void) | null>(null);

  /* ---------------------- */
  /* Detach previous handler */
  const cleanupMessageHandler = () => {
    if (messageHandlerRef.current && socket) {
      socket.removeEventListener("message", messageHandlerRef.current);
      messageHandlerRef.current = null;
    }
  };

  /* ---------------------- */
  /* Send user question      */
  async function handleSubmit(text?: string) {
    if (!socket || socket.readyState !== WebSocket.OPEN || isLoading) return;

    const userText = text || question;
    setIsLoading(true);
    cleanupMessageHandler();

    const traceId = uuidv4(); // ID for this round-trip

    // Add user message
    setMessages((prev) => [
      ...prev,
      { id: traceId, role: "user", content: userText }
    ]);

    socket.send(userText);
    setQuestion("");

    /* ---- New message handler ---- */
const handler = (event: MessageEvent) => {
  setIsLoading(false);
  if (event.data === "[END]") return;

  const raw = typeof event.data === "string" ? event.data : String(event.data);

  // If multiple JSON objects are concatenated, split them:  }{
  const chunks = raw.trim().startsWith("{")
    ? raw.replace(/}\s*{/g, "}\n{").split("\n")
    : [raw];

  for (const piece of chunks) {
    let payload: any = null;
    try {
      payload = JSON.parse(piece);
    } catch {
      /* not JSON -> treat as plain text */
    }
  console.log(
    "WS payload:",
    typeof payload,
    payload?.type,
    typeof payload?.data,
    (payload?.data || "").slice(0, 32),
    "len=",
    (payload?.data || "").length
  );

    // ---------- IMAGE branch ----------
    if (payload?.type === "image" && payload.data) {
      setMessages((prev) => [
        ...prev,
        { id: nanoid(), role: "assistant", imgSrc: payload.data }
      ]);
      continue;
    }

    // ---------- TEXT branch ----------
    const assistantText = payload?.data ?? piece;
    setMessages((prev) => {
      const last = prev.at(-1);
      const merged =
        last?.role === "assistant"
          ? (last.content ?? "") + assistantText
          : assistantText;

      const assistantMsg: message = {
        id: uuidv4(), // or keep your traceId if you prefer
        role: "assistant",
        content: merged
      };

      return last?.role === "assistant"
        ? [...prev.slice(0, -1), assistantMsg]
        : [...prev, assistantMsg];
    });
  }
};


    messageHandlerRef.current = handler;
    socket.addEventListener("message", handler);
  }

  /* ---------------------- */
  /* Render                  */
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

        <div
          ref={messagesEndRef}
          className="shrink-0 min-w-[24px] min-h-[24px]"
        />
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
