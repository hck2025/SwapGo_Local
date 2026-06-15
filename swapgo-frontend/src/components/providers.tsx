"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { WalletProvider } from "@/lib/wallet";
import { ToastProvider } from "@/components/toast";
import { WalletModalProvider } from "@/components/wallet-modal";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5_000,
            refetchOnWindowFocus: false,
          },
        },
      })
  );
  return (
    <QueryClientProvider client={client}>
      <WalletProvider>
        <ToastProvider>
          <WalletModalProvider>{children}</WalletModalProvider>
        </ToastProvider>
      </WalletProvider>
    </QueryClientProvider>
  );
}
