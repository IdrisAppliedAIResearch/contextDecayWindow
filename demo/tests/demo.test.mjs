import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);
const replayUrl = new URL("../app/data/study-003-replay.json", import.meta.url);

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the evidence replay shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>Memory Observatory · Context Decay Window<\/title>/i);
  assert.match(html, /Watch memory choose what matters\./);
  assert.match(html, /Replay Study 003/);
  assert.match(html, /study_003_full_002/);
  assert.match(html, /Qwen3\.6 27B/);
  assert.match(html, /Recorded evidence/);
  assert.match(html, /No live model call/);
  assert.doesNotMatch(html, /Your site is taking shape|codex-preview|react-loading-skeleton/);
});

test("ships all accepted transcript turns and canonical memory events", async () => {
  const replay = JSON.parse(await readFile(replayUrl, "utf8"));
  assert.equal(replay.schemaVersion, 1);
  assert.equal(replay.study.runId, "study_003_full_002");
  assert.equal(replay.study.model, "Qwen3.6 27B NVFP4");
  assert.equal(replay.study.rubricScore, 12);
  assert.equal(replay.study.rubricMax, 13);
  assert.equal(replay.study.peakContextTokens, 9189);
  assert.equal(replay.study.peakContextTurn, 80);

  assert.equal(replay.turns.length, 120);
  assert.deepEqual(
    replay.turns.map((turn) => turn.turn),
    Array.from({ length: 120 }, (_, index) => index + 1),
  );
  assert.ok(replay.turns.every((turn) => turn.user && turn.assistant));

  const ltmTurns = replay.turns.filter((turn) => turn.ltmEvent);
  assert.deepEqual(
    ltmTurns.map((turn) => turn.turn),
    [31, 61, 91],
  );
  assert.deepEqual(
    ltmTurns.map((turn) => turn.ltmEvent.promoted),
    [12, 7, 2],
  );
  assert.equal(replay.turns.at(-1).memory.ltmEpisodes, 21);
  assert.equal(replay.turns.at(-1).memory.topicCount, 1);
  assert.match(replay.turns[111].user, /Halcyon Crossing/);
  assert.match(replay.turns[119].assistant, /Renaissance art/);
  assert.equal(replay.provenance.rawMetricsMatchCanonical, true);
  assert.match(replay.provenance.localTranscriptSha256, /^[a-f0-9]{64}$/);
  assert.equal(Object.keys(replay.provenance.canonicalArtifacts).length, 12);
});

test("keeps the demo self-contained and keyboard-operable", async () => {
  const [page, app, layout, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/memory-observatory.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(page, /<MemoryObservatory \/>/);
  assert.match(app, /event\.code === "Space"/);
  assert.match(app, /event\.code === "ArrowRight"/);
  assert.match(app, /const TURN_DURATION_MS = 5_000/);
  assert.match(app, /5s \/ turn/);
  assert.doesNotMatch(app, /0\.5×|1×|2×|speed-control/);
  assert.match(app, /aria-label="Active context window"/);
  assert.match(app, /aria-label="Replay controls"/);
  assert.doesNotMatch(app, /fetch\(|OpenAI|api[_-]?key/i);
  assert.doesNotMatch(layout, /codex-preview|_sites-preview/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton|drizzle|tailwind/);
  assert.doesNotMatch(await readFile(new URL("../app/globals.css", import.meta.url), "utf8"), /@import\s+["']tailwindcss/);

  await assert.rejects(readFile(new URL("../app/_sites-preview/SkeletonPreview.tsx", root), "utf8"));
});
