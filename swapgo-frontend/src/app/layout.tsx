import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Topbar } from "@/components/topbar";

export const metadata: Metadata = {
  title: "스왑고 SwapGo",
  description: "AI 기반 블록체인 DEX 모의거래 및 학습 플랫폼",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="min-h-screen antialiased">
        <Providers>
          <Topbar />
          <main className="mx-auto w-full max-w-[1200px] px-4 py-4">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
