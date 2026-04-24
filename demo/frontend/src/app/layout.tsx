import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RAG Pitfalls · Live Demo",
  description:
    "20 production RAG pitfalls, each with a live before/after demo. Companion to the HIT LLM Foundation talk.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-TW">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
