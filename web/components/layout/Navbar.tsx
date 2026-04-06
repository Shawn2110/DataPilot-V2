"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

export function Navbar() {
  return (
    <nav className="h-14 border-b bg-background flex items-center px-6 justify-between">
      <Link href="/" className="text-lg font-bold">
        Data<span className="text-primary">Pilot</span>
      </Link>
      <div className="flex items-center gap-4">
        <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
          Home
        </Link>
        <Link href="/">
          <Button variant="outline" size="sm">New Analysis</Button>
        </Link>
      </div>
    </nav>
  );
}
