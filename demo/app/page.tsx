import type { Metadata } from "next";
import { MemoryObservatory } from "./memory-observatory";

export const metadata: Metadata = {
  title: "Memory Observatory",
  description:
    "Replay the accepted 120-turn Context Decay Window study and inspect its active context, topics, and memory writes.",
};

export default function Home() {
  return <MemoryObservatory />;
}
