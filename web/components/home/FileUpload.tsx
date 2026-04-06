"use client";

import { useRef, useState } from "react";

/**
 * FileUpload — Drag-and-drop file upload component.
 */
export function FileUpload({
  onUpload,
  isUploading,
}: {
  onUpload: (file: File) => void;
  isUploading: boolean;
}) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  }

  function handleClick() {
    inputRef.current?.click();
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  }

  return (
    <div
      onClick={handleClick}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={`w-full max-w-lg border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
        isDragging
          ? "border-blue-500 bg-blue-500/10"
          : "border-zinc-700 hover:border-zinc-500 bg-zinc-900"
      }`}
    >
      {isUploading ? (
        <p className="text-zinc-400">Uploading...</p>
      ) : (
        <>
          <p className="text-lg font-medium mb-2 text-white">Drop your dataset here</p>
          <p className="text-sm text-zinc-500 mb-4">CSV, Excel (.xlsx, .xls)</p>
          <span className="inline-block px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-sm rounded-lg border border-zinc-600">
            Browse files
          </span>
        </>
      )}
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        onChange={handleChange}
        className="hidden"
      />
    </div>
  );
}
