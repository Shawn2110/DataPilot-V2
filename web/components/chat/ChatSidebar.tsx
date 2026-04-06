"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { saveMessage, getMessages } from "@/lib/db";

interface Message {
  id: string;
  role: "user" | "assistant" | "code" | "thinking" | "error";
  content: string;
}

/**
 * ChatSidebar — The chat panel next to JupyterLab.
 * Built with shadcn/ui components for a polished look.
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

  // Load saved messages from IndexedDB on mount
  useEffect(() => {
    if (!sessionId) return;
    getMessages(sessionId).then((saved) => {
      if (saved.length > 0) {
        setMessages(saved.map((m) => ({ id: m.id, role: m.role, content: m.content })));
      }
    }).catch(() => {}); // IndexedDB not available — ignore
  }, [sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function addMessage(role: Message["role"], content: string) {
    const id = Date.now().toString() + Math.random();
    setMessages((prev) => [...prev, { id, role, content }]);

    // Persist to IndexedDB (fire-and-forget)
    if (sessionId) {
      saveMessage({
        id,
        projectId: sessionId,
        role,
        content,
        createdAt: new Date().toISOString(),
      }).catch(() => {});
    }
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
    <div className="flex flex-col h-full bg-background text-foreground">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold">
            Data<span className="text-primary">Pilot</span>
          </h2>
          <Badge variant="secondary" className="text-[10px]">v2</Badge>
        </div>
        <p className="text-xs text-muted-foreground mt-1">AI Data Science Copilot</p>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-3">
          {messages.map((msg) => {
            if (msg.role === "user") {
              return (
                <div key={msg.id} className="flex justify-end">
                  <div className="bg-primary text-primary-foreground rounded-lg rounded-br-sm px-3 py-2 text-sm max-w-[85%]">
                    {msg.content}
                  </div>
                </div>
              );
            }

            if (msg.role === "code") {
              return (
                <Card key={msg.id} className="bg-muted/50 border-border">
                  <CardContent className="p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="text-[10px]">code</Badge>
                      <span className="text-[10px] text-muted-foreground">inserted into notebook</span>
                    </div>
                    <pre className="text-xs font-mono whitespace-pre-wrap overflow-x-auto leading-relaxed">
                      {msg.content}
                    </pre>
                  </CardContent>
                </Card>
              );
            }

            if (msg.role === "thinking") {
              return (
                <div key={msg.id} className="text-muted-foreground italic text-xs px-1">
                  {msg.content}
                </div>
              );
            }

            if (msg.role === "error") {
              return (
                <Card key={msg.id} className="border-destructive/50 bg-destructive/10">
                  <CardContent className="p-3 text-sm text-destructive">
                    {msg.content}
                  </CardContent>
                </Card>
              );
            }

            // assistant
            return (
              <div key={msg.id} className="flex justify-start">
                <div className="bg-muted rounded-lg rounded-bl-sm px-3 py-2 text-sm max-w-[85%] whitespace-pre-wrap">
                  {msg.content}
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      <Separator />

      {/* Input */}
      <div className="p-3 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          placeholder="Ask DataPilot..."
          disabled={isLoading}
          className="flex-1 bg-muted text-foreground rounded-lg px-3 py-2 text-sm border border-border focus:border-ring focus:outline-none disabled:opacity-50"
        />
        <Button onClick={handleSend} disabled={isLoading} size="sm">
          {isLoading ? "..." : "Send"}
        </Button>
      </div>
    </div>
  );
}
