"use client";

import { useEffect, useRef } from "react";
import type { ChatMessageClient } from "../../types";
import { MessageBubble } from "./MessageBubble";

export function MessageList({ messages }: { messages: ChatMessageClient[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (!messages.length) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-500 text-sm px-6 text-center">
        選一個 scenario 或直接提問 —<br />
        Pick a scenario above, or ask anything to smoke-test the stack.
      </div>
    );
  }
  return (
    <div className="flex-1 overflow-y-auto space-y-3 p-3">
      {messages.map((m) => (
        <MessageBubble m={m} key={m.id} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
