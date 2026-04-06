"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { FileUpload } from "@/components/home/FileUpload";
import { Card, CardContent } from "@/components/ui/card";

export default function Home() {
  const router = useRouter();
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload(file: File) {
    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"}/api/upload`,
        { method: "POST", body: formData }
      );

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }

      const data = await res.json();
      router.push(`/workspace?session=${data.session_id}`);
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <main className="flex-1 flex flex-col items-center justify-center p-8">
      {/* Hero */}
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold mb-4">
          Data<span className="text-primary">Pilot</span>
        </h1>
        <p className="text-xl text-muted-foreground max-w-xl mx-auto">
          AI-powered data science copilot. Upload your data, chat with the agent,
          and watch it generate code in a Jupyter notebook.
        </p>
      </div>

      {/* Upload */}
      <FileUpload onUpload={handleUpload} isUploading={isUploading} />

      {error && (
        <p className="mt-4 text-destructive text-sm">{error}</p>
      )}

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-16 max-w-3xl w-full">
        {[
          { title: "Chat-Driven", desc: "Tell the AI what to analyze in plain English" },
          { title: "Jupyter Notebook", desc: "All code runs in a real notebook you can edit" },
          { title: "Free & Local", desc: "Runs on Ollama — no API keys, no cloud costs" },
        ].map((f) => (
          <Card key={f.title}>
            <CardContent className="p-6 text-center">
              <h3 className="font-semibold mb-1">{f.title}</h3>
              <p className="text-sm text-muted-foreground">{f.desc}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  );
}
