"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

/**
 * Home page — Upload a dataset to start analyzing.
 *
 * Flow:
 *   1. User drags/drops or selects a CSV/Excel file
 *   2. File is uploaded to the backend (POST /api/upload)
 *   3. Backend creates a session, returns session_id
 *   4. User is redirected to /workspace?session={id}
 */
export default function Home() {
  const router = useRouter();
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(file: File) {
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

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <main className="flex-1 flex flex-col items-center justify-center p-8 bg-gray-950 text-white">
      <div className="text-center mb-12">
        <h1 className="text-5xl font-bold mb-4">
          Data<span className="text-blue-400">Pilot</span>
        </h1>
        <p className="text-xl text-gray-400 max-w-xl">
          AI-powered data science copilot. Upload your data, chat with the agent,
          and watch it generate code in a Jupyter notebook.
        </p>
      </div>

      <div
        className={`w-full max-w-lg border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all ${
          isDragging
            ? "border-blue-400 bg-blue-400/10"
            : "border-gray-700 hover:border-gray-500 bg-gray-900"
        }`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById("fileInput")?.click()}
      >
        {isUploading ? (
          <p className="text-gray-400">Uploading...</p>
        ) : (
          <div>
            <p className="text-lg font-medium mb-2">Drop your dataset here</p>
            <p className="text-sm text-gray-500">CSV, Excel (.xlsx, .xls)</p>
          </div>
        )}
        <input
          id="fileInput"
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileInput}
          className="hidden"
        />
      </div>

      {error && <p className="mt-4 text-red-400 text-sm">{error}</p>}

      <div className="grid grid-cols-3 gap-6 mt-16 max-w-3xl">
        {[
          { title: "Chat-Driven", desc: "Tell the AI what to analyze in plain English" },
          { title: "Jupyter Notebook", desc: "All code runs in a real notebook you can edit" },
          { title: "Free & Local", desc: "Runs on Ollama — no API keys, no cloud costs" },
        ].map((f) => (
          <div key={f.title} className="text-center p-4">
            <h3 className="font-semibold mb-1">{f.title}</h3>
            <p className="text-sm text-gray-500">{f.desc}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
