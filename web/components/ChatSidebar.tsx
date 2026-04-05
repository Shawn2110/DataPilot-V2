"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
  id: string;
  role: "user" | "assistant" | "code" | "thinking" | "error";
  content: string;
}

/**
 * ChatSidebar — The chat panel next to JupyterLab.
 *
 * Users type instructions here. The agent responds with:
 *   - Thinking text (what it's reasoning about)
 *   - Code blocks (inserted into the notebook)
 *   - Natural language explanations
 */
export function ChatSidebar({ sessionId }: { sessionId: string }) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi! I'm DataPilot. Your data is loaded. What would you like to do?\n\nTry: \"show missing values\", \"plot age distribution\", or \"train a random forest\"",
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function addMessage(role: Message["role"], content: string) {
    setMessages((prev) => [
      ...prev,
      { id: Date.now().toString(), role, content },
    ]);
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || isLoading) return;

    setInput("");
    addMessage("user", text);
    setIsLoading(true);

    try {
      const res = await fetch(`${backendUrl}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      });

      if (!res.ok || !res.body) {
        addMessage("error", `Backend error: ${res.statusText}`);
        setIsLoading(false);
        return;
      }

      // Read SSE stream
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith("data: ")) {
            try {
              const event = JSON.parse(trimmed.slice(6));
              if (event.type === "code") {
                addMessage("code", event.content);
              } else if (event.type === "message" && event.content?.trim()) {
                addMessage("assistant", event.content);
              } else if (event.type === "thinking") {
                addMessage("thinking", event.content);
              } else if (event.type === "error") {
                addMessage("error", event.content);
              }
            } catch {}
          }
        }
      }
    } catch (err: any) {
      addMessage("error", `Connection failed: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <h2 className="text-lg font-bold">
          Data<span className="text-blue-400">Pilot</span>
        </h2>
        <p className="text-xs text-gray-500 mt-1">AI Data Science Copilot</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`rounded-lg px-3 py-2 text-sm leading-relaxed ${
              msg.role === "user"
                ? "bg-blue-600 text-white ml-8"
                : msg.role === "code"
                ? "bg-gray-800 border border-gray-700 font-mono text-xs whitespace-pre-wrap"
                : msg.role === "thinking"
                ? "text-gray-500 italic text-xs"
                : msg.role === "error"
                ? "bg-red-900/30 border border-red-800 text-red-300"
                : "bg-gray-800 text-gray-200 mr-8"
            }`}
          >
            {msg.role === "code" && (
              <div className="text-[10px] text-gray-500 mb-1">
                Code inserted into notebook
              </div>
            )}
            {msg.content}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-gray-800 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          placeholder="Ask DataPilot..."
          disabled={isLoading}
          className="flex-1 bg-gray-800 text-white rounded-lg px-3 py-2 text-sm border border-gray-700 focus:border-blue-500 focus:outline-none disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={isLoading}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium"
        >
          {isLoading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
