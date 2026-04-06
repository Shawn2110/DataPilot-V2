"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

/**
 * CodeBlock — Displays generated code in the chat sidebar.
 * Shows the code that was inserted into the Jupyter notebook.
 */
export function CodeBlock({ code }: { code: string }) {
  return (
    <Card className="bg-muted/50 border-border">
      <CardContent className="p-3">
        <div className="flex items-center gap-2 mb-2">
          <Badge variant="outline" className="text-[10px]">code</Badge>
          <span className="text-[10px] text-muted-foreground">
            inserted into notebook
          </span>
        </div>
        <pre className="text-xs font-mono whitespace-pre-wrap overflow-x-auto leading-relaxed">
          {code}
        </pre>
      </CardContent>
    </Card>
  );
}
