"use client";

import {
  Fragment,
  type CSSProperties,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import replay from "./data/study-003-replay.json";

type PlaybackStage = "user" | "assistant";
type ReplayTurn = (typeof replay.turns)[number];

const TURN_DURATION_MS = 5_000;
const USER_STAGE_MS = 1_000;
const ASSISTANT_STAGE_MS = TURN_DURATION_MS - USER_STAGE_MS;
const BOOKMARKS = [
  { turn: 3, label: "Plant facts" },
  { turn: 31, label: "LTM write 01" },
  { turn: 61, label: "LTM write 02" },
  { turn: 91, label: "LTM write 03" },
  { turn: 112, label: "Recall probes" },
  { turn: 120, label: "Coverage miss" },
] as const;

const TOPIC_BY_ID = new Map(replay.topics.map((topic) => [topic.id, topic]));

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function shortText(value: string, limit = 88) {
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > limit
    ? `${normalized.slice(0, limit).trimEnd()}…`
    : normalized;
}

function topicProgress(
  currentTurn: number,
  topic: (typeof replay.topics)[number],
) {
  if (currentTurn < topic.turnStart) return 0;
  if (currentTurn > topic.turnEnd) return 100;
  return (
    ((currentTurn - topic.turnStart + 1) /
      (topic.turnEnd - topic.turnStart + 1)) *
    100
  );
}

function InlineMarkdown({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, index) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>
        ) : (
          <Fragment key={`${part}-${index}`}>{part}</Fragment>
        ),
      )}
    </>
  );
}

function MessageText({ text }: { text: string }) {
  return (
    <div className="message-copy">
      {text.split("\n").map((line, index) => {
        const numbered = line.match(/^(\s*)(\d+)\.\s+(.*)$/);
        if (numbered) {
          return (
            <div
              className="numbered-line"
              key={`${index}-${line.slice(0, 24)}`}
              style={{ "--indent": numbered[1].length } as CSSProperties}
            >
              <span className="numbered-line-index">{numbered[2]}</span>
              <span>
                <InlineMarkdown text={numbered[3]} />
              </span>
            </div>
          );
        }

        if (!line.trim()) {
          return <span className="message-break" key={`break-${index}`} />;
        }

        return (
          <p key={`${index}-${line.slice(0, 24)}`}>
            <InlineMarkdown text={line} />
          </p>
        );
      })}
    </div>
  );
}

function BrandMark({ small = false }: { small?: boolean }) {
  return (
    <span className={`brand-mark${small ? " brand-mark-small" : ""}`} aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  );
}

function TopicSidebar({
  currentTurn,
  onSeek,
}: {
  currentTurn: number;
  onSeek: (turn: number) => void;
}) {
  return (
    <aside className="topic-sidebar" aria-label="Conversation topics">
      <div className="brand-lockup">
        <BrandMark />
        <div>
          <span className="brand-kicker">Context Decay Window</span>
          <span className="brand-name">Memory Observatory</span>
        </div>
      </div>

      <div className="sidebar-section-heading">
        <span>Conversation map</span>
        <span>{currentTurn}/120</span>
      </div>

      <nav className="topic-list">
        {replay.topics.map((topic) => {
          const active =
            currentTurn >= topic.turnStart && currentTurn <= topic.turnEnd;
          const completed = currentTurn > topic.turnEnd;
          return (
            <button
              className={`topic-item topic-${topic.accent}${active ? " is-active" : ""}${completed ? " is-complete" : ""}`}
              key={topic.id}
              onClick={() => onSeek(topic.turnStart)}
              type="button"
              aria-current={active ? "step" : undefined}
            >
              <span className="topic-rail" aria-hidden="true">
                <span
                  className="topic-rail-fill"
                  style={{ width: `${topicProgress(currentTurn, topic)}%` }}
                />
              </span>
              <span className="topic-item-row">
                <span className="topic-dot" aria-hidden="true" />
                <span className="topic-label">{topic.label}</span>
                <span className="topic-range">
                  {topic.turnStart}–{topic.turnEnd}
                </span>
              </span>
              <span className="topic-description">{topic.description}</span>
            </button>
          );
        })}
      </nav>

      <section className="pinned-card" aria-labelledby="pinned-memory-title">
        <div className="pinned-card-heading">
          <span className="pin-icon" aria-hidden="true" />
          <span id="pinned-memory-title">Pinned memory</span>
          <span className="memory-health">2 rules</span>
        </div>
        <ol>
          {replay.pinnedRules.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ol>
        <span className="pinned-footnote">Available outside episodic retrieval</span>
      </section>

      <div className="sidebar-provenance">
        <span className="verified-dot" aria-hidden="true" />
        <div>
          <strong>Accepted evidence</strong>
          <span>Study 003 · run full_002</span>
        </div>
      </div>
    </aside>
  );
}

function ContextStrip({ turn }: { turn: ReplayTurn | null }) {
  const context = turn?.context;
  const topic = turn ? TOPIC_BY_ID.get(turn.topic) : null;
  const tokenShare = context
    ? Math.min((context.estimatedTokens / replay.study.peakContextTokens) * 100, 100)
    : 0;

  return (
    <section className="context-strip" aria-label="Active context window">
      <div className="context-strip-title">
        <span className="eyebrow">Active context window</span>
        <strong>{context ? `${context.uniqueEpisodes} episodes` : "Standing by"}</strong>
      </div>

      <div className="context-composition" aria-label="Context composition">
        <span className="composition-segment segment-k">
          <span>K</span>
          <strong>{context?.kCount ?? 0}</strong>
          <small>similar</small>
        </span>
        <span className="composition-plus" aria-hidden="true">+</span>
        <span className="composition-segment segment-n">
          <span>N</span>
          <strong>{context?.nCount ?? 0}</strong>
          <small>decayed</small>
        </span>
        <span className="composition-plus" aria-hidden="true">+</span>
        <span className="composition-segment segment-rules">
          <span>R</span>
          <strong>{turn?.memory.ruleCount ?? 0}</strong>
          <small>pinned</small>
        </span>
      </div>

      <div className="token-meter">
        <div className="token-meter-label">
          <span>Constructed prompt</span>
          <strong>{context ? `${formatNumber(context.estimatedTokens)} tokens` : "—"}</strong>
        </div>
        <span className="token-track" aria-hidden="true">
          <span style={{ width: `${tokenShare}%` }} />
        </span>
        <small>
          {context
            ? `${((context.estimatedTokens / replay.study.contextCapacity) * 100).toFixed(2)}% of model capacity`
            : `Peak observed: ${formatNumber(replay.study.peakContextTokens)}`}
        </small>
      </div>

      <div className="current-topic">
        <span className={`topic-dot topic-dot-${topic?.accent ?? "muted"}`} aria-hidden="true" />
        <span>
          <small>Now tracking</small>
          <strong>{topic?.label ?? "Replay not started"}</strong>
        </span>
      </div>
    </section>
  );
}

function LtmEventCard({ turn }: { turn: ReplayTurn }) {
  if (!turn.ltmEvent) return null;
  const number = [31, 61, 91].indexOf(turn.turn) + 1;
  return (
    <div className="system-event ltm-system-event" role="status">
      <span className="event-pulse" aria-hidden="true" />
      <div className="event-copy">
        <span className="event-kicker">Topic transition · LTM write 0{number}</span>
        <strong>
          {turn.ltmEvent.promoted} of {turn.ltmEvent.evaluated} outgoing episodes promoted
        </strong>
        <span>
          Long-term store now holds {turn.ltmEvent.ltmTotal} episodes · write-only during this study
        </span>
      </div>
      <span className="event-rate">
        {(turn.ltmEvent.rate * 100).toFixed(1)}%
        <small>promotion rate</small>
      </span>
    </div>
  );
}

function ConsolidationEvent({ turn }: { turn: ReplayTurn }) {
  if (!turn.consolidation || turn.ltmEvent) return null;
  const merged = turn.consolidation.pairsMerged > 0;
  return (
    <div className={`system-event consolidation-event${merged ? " merged" : ""}`}>
      <span className="consolidation-symbol" aria-hidden="true">⇢</span>
      <span>
        <strong>Consolidation checkpoint</strong>
        {merged
          ? ` · ${turn.consolidation.topicsBefore} → ${turn.consolidation.topicsAfter} topics`
          : ` · ${turn.consolidation.topicsAfter} topics retained`}
      </span>
    </div>
  );
}

function Exchange({
  turn,
  current,
  showAssistant,
  expanded,
  onToggleExpanded,
}: {
  turn: ReplayTurn;
  current: boolean;
  showAssistant: boolean;
  expanded: boolean;
  onToggleExpanded: (turn: number) => void;
}) {
  const topic = TOPIC_BY_ID.get(turn.topic);
  const responseIsLong = turn.assistant.length > 720;

  return (
    <article className={`exchange${current ? " is-current" : ""}`} data-turn={turn.turn}>
      <div className="turn-divider">
        <span>Turn {String(turn.turn).padStart(3, "0")}</span>
        <span className={`turn-topic topic-${topic?.accent ?? "muted"}`}>
          {turn.phase === "probe" ? `Probe · ${turn.queryDomain}` : topic?.shortLabel}
        </span>
      </div>

      <div className="message-row user-row">
        <div className="message-bubble user-message">
          <MessageText text={turn.user} />
        </div>
        <span className="avatar user-avatar" aria-hidden="true">M</span>
      </div>

      {showAssistant ? (
        <>
          <div className="message-row assistant-row">
            <span className="avatar assistant-avatar" aria-hidden="true">
              <BrandMark small />
            </span>
            <div className="assistant-message-wrap">
              <div
                className={`message-bubble assistant-message${expanded ? " is-expanded" : ""}`}
              >
                <MessageText text={turn.assistant} />
                {responseIsLong && !expanded ? <span className="message-fade" /> : null}
              </div>
              {responseIsLong ? (
                <button
                  className="expand-response"
                  type="button"
                  onClick={() => onToggleExpanded(turn.turn)}
                >
                  {expanded ? "Collapse response" : "Read full recorded response"}
                </button>
              ) : null}
              <div className="response-meta">
                <span>{turn.performance.outputTokens} output tokens</span>
                <span>{turn.performance.tokensPerSecond.toFixed(1)} tok/s</span>
                <span>{turn.performance.timeToFirstTokenMs.toFixed(1)} ms TTFT</span>
              </div>
            </div>
          </div>
          <LtmEventCard turn={turn} />
          <ConsolidationEvent turn={turn} />
          {turn.turn === 120 ? (
            <div className="system-event coverage-event">
              <span className="coverage-symbol" aria-hidden="true">!</span>
              <span>
                <strong>Coverage miss surfaced</strong>
                The broad all-domain query omitted Renaissance art and monetary policy evidence.
              </span>
            </div>
          ) : null}
        </>
      ) : (
        <div className="message-row assistant-row typing-row" aria-label="Recorded assistant response arriving">
          <span className="avatar assistant-avatar" aria-hidden="true">
            <BrandMark small />
          </span>
          <span className="typing-indicator" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
        </div>
      )}
    </article>
  );
}

function IntroCard({ onStart }: { onStart: () => void }) {
  return (
    <section className="intro-card">
      <div className="intro-orbit" aria-hidden="true">
        <span className="orbit orbit-one" />
        <span className="orbit orbit-two" />
        <span className="orbit orbit-three" />
        <BrandMark />
      </div>
      <span className="eyebrow intro-eyebrow">A real 120-turn evidence replay</span>
      <h1>Watch memory choose what matters.</h1>
      <p>
        A bounded context window retrieves relevant episodes, preserves rules, consolidates topics,
        and selectively writes to long-term memory—without replaying the entire conversation to the model.
      </p>
      <button className="primary-demo-button" type="button" onClick={onStart} data-testid="start-demo">
        <span className="play-glyph" aria-hidden="true" />
        Replay Study 003
        <small>5 seconds per turn</small>
      </button>
      <div className="intro-proof">
        <span>
          <strong>12 / 13</strong>
          recall rubric
        </span>
        <span>
          <strong>21 / 90</strong>
          LTM promotions
        </span>
        <span>
          <strong>9,189</strong>
          peak prompt tokens
        </span>
      </div>
      <span className="intro-disclosure">
        Recorded Qwen3.6 run · No live model call · Every value is linked to the accepted artifacts
      </span>
    </section>
  );
}

function OutcomeCard({ onReplay }: { onReplay: () => void }) {
  return (
    <section className="outcome-card" aria-labelledby="outcome-title">
      <div className="outcome-heading">
        <span className="outcome-status">Study outcome · Partial</span>
        <h2 id="outcome-title">Targeted memory held. Broad coverage did not.</h2>
        <p>
          The architecture preserved early, middle, and late planted facts across four domains,
          while the final all-domain enumeration exposed a retrieval coverage gap.
        </p>
      </div>
      <div className="outcome-grid">
        <div className="outcome-metric positive">
          <span>Recall</span>
          <strong>12<span>/13</span></strong>
          <small>one broad-query miss</small>
        </div>
        <div className="outcome-metric positive">
          <span>Success bars</span>
          <strong>2<span>/3</span></strong>
          <small>middle recall preserved</small>
        </div>
        <div className="outcome-metric neutral">
          <span>LTM writes</span>
          <strong>21</strong>
          <small>from 90 evaluated episodes</small>
        </div>
        <div className="outcome-metric caution">
          <span>Final topics</span>
          <strong>1</strong>
          <small>count passed; purity caveat</small>
        </div>
      </div>
      <div className="outcome-actions">
        <button className="secondary-button" type="button" onClick={onReplay}>
          Replay from turn 1
        </button>
        <a
          className="text-link"
          href="https://github.com/IdrisAppliedAIResearch/contextDecayWindow/tree/main/experiments/study_003"
          target="_blank"
          rel="noreferrer"
        >
          Read the paper <span aria-hidden="true">↗</span>
        </a>
      </div>
    </section>
  );
}

function EvidenceRail({ turn, currentTurn }: { turn: ReplayTurn | null; currentTurn: number }) {
  const contextEntries = turn?.context.entries ?? [];
  const latestEntries = [...contextEntries].reverse().slice(0, 7);
  const processed = replay.turns.slice(0, currentTurn);
  const recentEvents = processed
    .flatMap((item) => {
      const events: { turn: number; type: string; text: string }[] = [];
      if (item.ltmEvent) {
        events.push({
          turn: item.turn,
          type: "ltm",
          text: `${item.ltmEvent.promoted} promoted · ${item.ltmEvent.ltmTotal} total`,
        });
      } else if (item.consolidation?.pairsMerged) {
        events.push({
          turn: item.turn,
          type: "merge",
          text: `${item.consolidation.topicsBefore} → ${item.consolidation.topicsAfter} topics`,
        });
      } else if (item.memory.newTopic) {
        events.push({ turn: item.turn, type: "topic", text: "New topic detected" });
      }
      if (item.rule.detected) {
        events.push({ turn: item.turn, type: "rule", text: "Persistent rule pinned" });
      }
      return events;
    })
    .slice(-4)
    .reverse();

  return (
    <aside className="evidence-rail" aria-label="Memory telemetry">
      <section className="telemetry-card memory-stack-card">
        <div className="card-heading">
          <span>Memory stores</span>
          <span className="live-indicator"><i /> live replay</span>
        </div>
        <div className="memory-stack">
          <div className="store-card stm-store">
            <div>
              <span>Short-term memory</span>
              <small>episodic source store</small>
            </div>
            <strong>{turn?.memory.stmEpisodes ?? 0}</strong>
          </div>
          <div className="store-flow" aria-hidden="true">
            <span />
            <small>4-filter promotion</small>
            <span />
          </div>
          <div className={`store-card ltm-store${turn?.ltmEvent ? " is-writing" : ""}`}>
            <div>
              <span>Long-term memory</span>
              <small>write-only in Study 003</small>
            </div>
            <strong>{turn?.memory.ltmEpisodes ?? 0}</strong>
          </div>
        </div>
        <div className="promotion-meter">
          <span>
            <strong>{turn?.memory.ltmEpisodes ?? 0}</strong> promoted so far
          </span>
          <span>{Math.min(((turn?.memory.ltmEpisodes ?? 0) / 21) * 100, 100).toFixed(0)}%</span>
          <i aria-hidden="true">
            <b style={{ width: `${Math.min(((turn?.memory.ltmEpisodes ?? 0) / 21) * 100, 100)}%` }} />
          </i>
        </div>
      </section>

      <section className="telemetry-card retrieved-card">
        <div className="card-heading">
          <span>Retrieved now</span>
          <span>{contextEntries.length} unique</span>
        </div>
        {latestEntries.length ? (
          <div className="retrieved-list">
            {latestEntries.map((entry) => {
              const source = replay.turns[entry.sourceTurn - 1];
              return (
                <div className="retrieved-item" key={entry.episodeId}>
                  <span className={`retrieval-badge retrieval-${entry.retrievalType.toLowerCase().replace("+", "n")}`}>
                    {entry.retrievalType}
                  </span>
                  <div>
                    <span>Turn {String(entry.sourceTurn).padStart(3, "0")}</span>
                    <p>{shortText(source.user, 68)}</p>
                  </div>
                  <small>{entry.similarity ? entry.similarity.toFixed(2) : entry.decay.toFixed(2)}</small>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="empty-telemetry">
            <span className="empty-rings" aria-hidden="true" />
            <p>Retrieved episodes will appear here as the replay advances.</p>
          </div>
        )}
      </section>

      <section className="telemetry-card event-log-card">
        <div className="card-heading">
          <span>Architecture events</span>
          <span>latest</span>
        </div>
        {recentEvents.length ? (
          <ol className="event-log">
            {recentEvents.map((event, index) => (
              <li key={`${event.turn}-${event.type}-${index}`}>
                <span className={`log-dot log-${event.type}`} aria-hidden="true" />
                <div>
                  <strong>{event.text}</strong>
                  <span>Turn {String(event.turn).padStart(3, "0")}</span>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <p className="empty-log">Waiting for the first stored episode.</p>
        )}
      </section>

      <section className="evidence-note">
        <span className="verified-dot" aria-hidden="true" />
        <p>
          <strong>Evidence mode</strong>
          Transcript content and telemetry are replayed from the accepted run, not generated in-browser.
        </p>
      </section>
    </aside>
  );
}

function PlaybackDock({
  started,
  playing,
  complete,
  currentTurn,
  onToggle,
  onReset,
  onSeek,
}: {
  started: boolean;
  playing: boolean;
  complete: boolean;
  currentTurn: number;
  onToggle: () => void;
  onReset: () => void;
  onSeek: (turn: number) => void;
}) {
  return (
    <footer className="playback-dock" aria-label="Replay controls">
      <button
        className="round-control"
        type="button"
        onClick={complete ? onReset : onToggle}
        aria-label={complete ? "Replay from the beginning" : playing ? "Pause replay" : "Play replay"}
        disabled={!started}
        data-testid="playback-toggle"
      >
        <span className={complete ? "replay-glyph" : playing ? "pause-glyph" : "play-glyph"} aria-hidden="true" />
      </button>

      <div className="playback-progress">
        <div className="playback-progress-label">
          <span>{complete ? "Replay complete" : started ? `Turn ${currentTurn} of 120` : "Ready to replay"}</span>
          <span>{Math.round((currentTurn / 120) * 100)}%</span>
        </div>
        <input
          aria-label="Study turn"
          type="range"
          min="1"
          max="120"
          value={Math.max(currentTurn, 1)}
          onChange={(event) => onSeek(Number(event.target.value))}
          style={{ "--progress": `${Math.max((currentTurn / 120) * 100, 0)}%` } as CSSProperties}
        />
        <div className="timeline-markers" aria-hidden="true">
          {[31, 61, 91, 112].map((marker) => (
            <span key={marker} style={{ left: `${((marker - 1) / 119) * 100}%` }} />
          ))}
        </div>
      </div>

      <span className="turn-pacing" aria-label="Replay pacing">5s / turn</span>
    </footer>
  );
}

export function MemoryObservatory() {
  const [started, setStarted] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [complete, setComplete] = useState(false);
  const [cursor, setCursor] = useState(0);
  const [stage, setStage] = useState<PlaybackStage>("user");
  const [expandedTurns, setExpandedTurns] = useState<Set<number>>(() => new Set());
  const chatRef = useRef<HTMLDivElement>(null);

  const current = started ? replay.turns[cursor] : null;
  const currentTurn = current?.turn ?? 0;

  const start = useCallback(() => {
    setStarted(true);
    setPlaying(true);
    setComplete(false);
    setCursor(0);
    setStage("user");
    setExpandedTurns(new Set());
  }, []);

  const seek = useCallback((turn: number) => {
    const bounded = Math.min(Math.max(turn, 1), replay.turns.length);
    setStarted(true);
    setPlaying(false);
    setComplete(false);
    setCursor(bounded - 1);
    setStage("assistant");
  }, []);

  const togglePlayback = useCallback(() => {
    if (!started) return;
    if (complete) {
      start();
      return;
    }
    setPlaying((value) => !value);
  }, [complete, start, started]);

  const toggleExpanded = useCallback((turn: number) => {
    setExpandedTurns((existing) => {
      const next = new Set(existing);
      if (next.has(turn)) next.delete(turn);
      else next.add(turn);
      return next;
    });
  }, []);

  useEffect(() => {
    if (!playing || !started || complete) return;

    const delay = stage === "user" ? USER_STAGE_MS : ASSISTANT_STAGE_MS;

    const timer = window.setTimeout(() => {
      if (stage === "user") {
        setStage("assistant");
        return;
      }

      if (cursor >= replay.turns.length - 1) {
        setPlaying(false);
        setComplete(true);
        return;
      }

      setCursor((value) => value + 1);
      setStage("user");
    }, delay);

    return () => window.clearTimeout(timer);
  }, [complete, cursor, playing, stage, started]);

  useEffect(() => {
    if (!started || !chatRef.current) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    chatRef.current.scrollTo({
      top: chatRef.current.scrollHeight,
      behavior: reduceMotion ? "auto" : "smooth",
    });
  }, [cursor, stage, started, complete]);

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.matches("input, button, a, textarea, select")) return;
      if (event.code === "Space") {
        event.preventDefault();
        togglePlayback();
      } else if (event.code === "ArrowRight") {
        seek(Math.min(currentTurn + 1, 120));
      } else if (event.code === "ArrowLeft") {
        seek(Math.max(currentTurn - 1, 1));
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [currentTurn, seek, togglePlayback]);

  const visibleTurns = useMemo(() => {
    if (!started) return [];
    const startIndex = Math.max(0, cursor - 4);
    return replay.turns.slice(startIndex, cursor + 1);
  }, [cursor, started]);

  return (
    <main className="observatory-shell">
      <TopicSidebar currentTurn={currentTurn} onSeek={seek} />

      <section className="conversation-workspace">
        <header className="workspace-header">
          <div className="mobile-brand">
            <BrandMark small />
            <span>Memory Observatory</span>
          </div>
          <div className="run-identity">
            <span className="status-chip"><i /> accepted run</span>
            <span>study_003_full_002</span>
            <span className="header-divider" />
            <span>Qwen3.6 27B · NVFP4</span>
          </div>
          <div className="header-actions">
            <span className="recorded-chip">Recorded evidence</span>
            <a
              href="https://github.com/IdrisAppliedAIResearch/contextDecayWindow"
              target="_blank"
              rel="noreferrer"
            >
              Source <span aria-hidden="true">↗</span>
            </a>
          </div>
        </header>

        <ContextStrip turn={current} />

        <nav className="bookmark-strip" aria-label="Key study moments">
          <span>Jump to</span>
          {BOOKMARKS.map((bookmark) => (
            <button
              key={bookmark.turn}
              type="button"
              className={currentTurn === bookmark.turn ? "is-active" : ""}
              onClick={() => seek(bookmark.turn)}
            >
              <span>{String(bookmark.turn).padStart(3, "0")}</span>
              {bookmark.label}
            </button>
          ))}
        </nav>

        <div className="chat-viewport" ref={chatRef}>
          <div className="chat-column">
            {!started ? <IntroCard onStart={start} /> : null}

            {started && !complete
              ? visibleTurns.map((turn) => {
                  const isCurrent = turn.turn === currentTurn;
                  return (
                    <Exchange
                      key={turn.turn}
                      turn={turn}
                      current={isCurrent}
                      showAssistant={!isCurrent || stage === "assistant"}
                      expanded={expandedTurns.has(turn.turn)}
                      onToggleExpanded={toggleExpanded}
                    />
                  );
                })
              : null}

            {complete ? <OutcomeCard onReplay={start} /> : null}
          </div>
        </div>

        <PlaybackDock
          started={started}
          playing={playing}
          complete={complete}
          currentTurn={currentTurn}
          onToggle={togglePlayback}
          onReset={start}
          onSeek={seek}
        />
      </section>

      <EvidenceRail turn={current} currentTurn={currentTurn} />
    </main>
  );
}
