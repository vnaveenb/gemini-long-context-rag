"use client";

import { ApiKeyProvider } from "@/context/ApiKeyContext";
import { Sidebar } from "@/components/Sidebar";

/**
 * Client-side providers wrapper. Layout.tsx is a server component
 * so we need a "use client" boundary here for context providers.
 */
export function ClientProviders({ children }: { children: React.ReactNode }) {
  return (
    <ApiKeyProvider>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">{children}</main>
      </div>
    </ApiKeyProvider>
  );
}
