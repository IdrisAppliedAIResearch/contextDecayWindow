import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Memory Observatory",
    template: "%s · Context Decay Window",
  },
  description:
    "An evidence-backed, interactive replay of a bounded conversational-memory architecture.",
  applicationName: "Context Decay Window",
  keywords: [
    "conversational memory",
    "long context",
    "retrieval",
    "long-term memory",
    "AI research",
  ],
  openGraph: {
    type: "website",
    title: "Memory Observatory",
    description: "Watch a bounded AI memory choose what matters across 120 turns.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Memory Observatory",
    description: "Watch a bounded AI memory choose what matters across 120 turns.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
