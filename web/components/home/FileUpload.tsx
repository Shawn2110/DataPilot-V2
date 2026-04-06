"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

/**
 * FileUpload — Drag-and-drop file upload component.
 * Used on the home page to upload datasets.
 */
export function FileUpload({
  onUpload,
  isUploading,
}: {
  onUpload: (file: File) => void;
  isUploading: boolean;
}) {
  const [isDragging, setIsDragging] = useState(false);

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  }

  return (
    <Card
      className={`w-full max-w-lg border-2 border-dashed cursor-pointer transition-all ${
        isDragging ? "border-primary bg-primary/5" : "border-border hover:border-muted-foreground"
      }`}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => document.getElementById("fileInput")?.click()}
    >
      <CardContent className="p-12 text-center">
        {isUploading ? (
          <p className="text-muted-foreground">Uploading...</p>
        ) : (
          <>
            <p className="text-lg font-medium mb-2">Drop your dataset here</p>
            <p className="text-sm text-muted-foreground mb-4">
              CSV, Excel (.xlsx, .xls)
            </p>
            <Button variant="secondary" size="sm">Browse files</Button>
          </>
        )}
        <input
          id="fileInput"
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onUpload(file);
          }}
          className="hidden"
        />
      </CardContent>
    </Card>
  );
}
