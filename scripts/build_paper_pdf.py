"""Typeset PAPER-002 as a PDF white paper, from the Markdown source.

The PDF has no independent source. This script reads `paper/PAPER_002.md`,
converts it to Typst, and compiles it, so the Markdown stays the single place
any claim is edited. If the two ever disagree, the Markdown is right and this
script is broken.

Two things it does beyond converting:

  * Figures are defined at the end of the Markdown, as a list. Here they are
    moved to the paragraph that first mentions them, which is what a reader of a
    typeset paper expects. Numbering comes from the Markdown, not from Typst, so
    the figure numbers cannot drift away from the prose that cites them.
  * Tables get proportional column widths derived from their content, because
    Typst's `auto` sizing does not wrap and this paper has one table with a very
    wide final column.

Requires the `typst` wheel:

    pip install typst

Usage, from the repository root:

    python scripts/build_paper_pdf.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / "paper/PAPER_002.md"
TYP = REPO / "paper/build/whitepaper.typ"
PDF = REPO / "paper/Rank_Fine_Pack_Fine_Call_Nothing.pdf"
FIGURES = REPO / "paper/figures"
PAPER_BUILD_TIMESTAMP = 1_786_579_200  # 2026-08-13 00:00:00 UTC

# Typst markup characters that must not be read as syntax inside body text.
_ESCAPE = str.maketrans({c: "\\" + c for c in "\\#$*_`<>@[]"})


def esc(text: str) -> str:
    """Escape a run of literal text for Typst markup mode."""
    out = text.translate(_ESCAPE)
    # A leading =, -, + or / would start a heading, list or term item.
    return re.sub(r"^([=\-+/])", r"\\\1", out)


_INLINE = re.compile(
    r"(?P<code>`[^`]+`)"
    r"|(?P<bold>\*\*[^*]+\*\*)"
    r"|(?P<italic>(?<!\*)\*(?!\*)[^*]+\*(?!\*))"
)


def typst_string(value: str) -> str:
    """Quote a Python string as a Typst string literal (double quotes only)."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def inline(md: str) -> str:
    """Convert inline Markdown to Typst, escaping everything else."""
    out, cursor = [], 0
    for match in _INLINE.finditer(md):
        out.append(esc(md[cursor : match.start()]))
        if match.group("code"):
            body = match.group("code")[1:-1]
            out.append(f"#raw({typst_string(body)})")
        elif match.group("bold"):
            out.append("*" + esc(match.group("bold")[2:-2]) + "*")
        else:
            out.append("_" + esc(match.group("italic")[1:-1]) + "_")
        cursor = match.end()
    out.append(esc(md[cursor:]))
    return "".join(out)


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def emit_table(rows: list[str]) -> str:
    """Convert a Markdown table to a Typst table with booktabs-style rules."""
    header = split_row(rows[0])
    aligns = []
    for spec in split_row(rows[1]):
        if spec.endswith(":") and spec.startswith(":"):
            aligns.append("center")
        elif spec.endswith(":"):
            aligns.append("right")
        else:
            aligns.append("left")
    body = [split_row(r) for r in rows[2:]]
    n = len(header)

    # Proportional widths: narrow columns stay auto, wide ones share the rest so
    # their text wraps instead of overflowing the page.
    widths = []
    for i in range(n):
        cells = [header[i]] + [r[i] for r in body if i < len(r)]
        longest = max(len(c) for c in cells)
        if longest <= 10:
            widths.append("auto")
        else:
            widths.append(f"{max(1.8, round(longest ** 0.55, 2))}fr")
    if all(w == "auto" for w in widths):
        widths[0] = "1fr"

    lines = [
        "#table(",
        f"  columns: ({', '.join(widths)}),",
        f"  align: ({', '.join(a + ' + top' for a in aligns)}),",
        "  stroke: none,",
        "  inset: (x: 5pt, y: 4pt),",
        "  table.hline(stroke: 0.9pt),",
        "  table.header(" + ", ".join(f"[*{inline(c)}*]" for c in header) + "),",
        "  table.hline(stroke: 0.5pt),",
    ]
    for row in body:
        cells = [inline(row[i]) if i < len(row) else "" for i in range(n)]
        lines.append("  " + ", ".join(f"[{c}]" for c in cells) + ",")
    lines += ["  table.hline(stroke: 0.9pt),", ")", ""]
    return "\n".join(lines)


def parse_blocks(text: str) -> list[tuple[str, object]]:
    """Split Markdown into typed blocks."""
    blocks: list[tuple[str, object]] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.strip() == "---":
            blocks.append(("rule", None))
            i += 1
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            blocks.append(("h", (level, line[level:].strip())))
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            blocks.append(("table", rows))
        elif re.match(r"^\s*[-*] ", line) or re.match(r"^\s*\d+\. ", line):
            items, ordered = [], bool(re.match(r"^\s*\d+\. ", line))
            while i < len(lines) and (
                re.match(r"^\s*[-*] ", lines[i]) or re.match(r"^\s*\d+\. ", lines[i])
                or (items and lines[i].startswith("  ") and lines[i].strip())
            ):
                if re.match(r"^\s*([-*]|\d+\.) ", lines[i]):
                    items.append(re.sub(r"^\s*([-*]|\d+\.) ", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            blocks.append(("list", (ordered, items)))
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(
                ("|", "#", "- ", "* ")
            ) and lines[i].strip() != "---":
                para.append(lines[i].strip())
                i += 1
            blocks.append(("p", " ".join(para)))
    return blocks


def extract_figures(blocks: list) -> tuple[list, dict[int, dict]]:
    """Pull the Figures section out of the flow and index it by number."""
    figures: dict[int, dict] = {}
    kept, in_figures = [], False
    for kind, value in blocks:
        if kind == "h" and value[1] == "Figures":
            in_figures = True
            continue
        if in_figures and kind == "h":
            in_figures = False
        if not in_figures:
            kept.append((kind, value))
            continue
        if kind == "p":
            match = re.match(r"^\*\*Figure (\d+) — (.+?)\.\*\* `([^`]+)` (.+)$", value)
            if match:
                number = int(match.group(1))
                figures[number] = {
                    "title": match.group(2),
                    "file": match.group(3),
                    "caption": match.group(4),
                }
    return kept, figures


def emit_figure(number: int, figure: dict) -> str:
    path = FIGURES / figure["file"]
    if not path.exists():  # SVG missing: fall back to the PNG twin.
        path = path.with_suffix(".png")
    # Root-absolute, because the .typ lives in paper/build/ while the images
    # live in paper/figures/ and Typst resolves relative paths against the file.
    rel = "/" + path.relative_to(REPO / "paper").as_posix()
    caption = (
        f"*Figure {number}. {inline(figure['title'])}.* "
        + inline(figure["caption"])
    )
    return (
        "#figure(\n"
        f'  image("{rel}", width: 100%),\n'
        "  numbering: none,\n"
        f"  caption: [{caption}],\n"
        ")\n"
    )


PREAMBLE = r"""
#set document(title: "Selection, Not Capacity", author: "Idris Applied AI Research")
#set page(
  paper: "a4",
  margin: (top: 2.4cm, bottom: 2.2cm, x: 2.3cm),
  footer: context [
    #set text(size: 8pt, fill: luma(45%))
    #line(length: 100%, stroke: 0.3pt + luma(75%))
    #v(-3pt)
    #grid(columns: (1fr, 1fr),
      align(left)[Idris Applied AI Research · PAPER-001],
      align(right)[#counter(page).display("1 of 1", both: true)])
  ],
)
#set text(font: "New Computer Modern", size: 10pt, lang: "en")
#set par(justify: true, leading: 0.62em, first-line-indent: 0pt, spacing: 0.9em)
#show raw: set text(font: "New Computer Modern Mono", size: 0.92em)
#set heading(numbering: none)

#show heading.where(level: 2): it => block(above: 1.5em, below: 0.75em)[
  #set text(size: 12.5pt, weight: "bold"); #it.body
]
#show heading.where(level: 3): it => block(above: 1.25em, below: 0.6em)[
  #set text(size: 10.8pt, weight: "bold"); #it.body
]
#show heading.where(level: 4): it => block(above: 1.1em, below: 0.5em)[
  #set text(size: 10pt, weight: "bold", style: "italic"); #it.body
]
#show figure: set block(breakable: false)
#show figure.caption: it => block(width: 100%, inset: (top: 4pt))[
  #set text(size: 8.4pt); #set par(justify: true, leading: 0.55em); #it.body
]
#set table(fill: (_, y) => if y == 0 { luma(96%) })
#show table: set text(size: 8.8pt)
#show table: set par(justify: false, leading: 0.52em)
"""


def title_block(raw_front_matter: str, blocks: list) -> tuple[str, list]:
    """Emit a typeset title block; return it with the remaining blocks."""
    title = blocks[0][1][1]
    subtitle = blocks[1][1][1]
    rest = blocks[3:]
    while rest and rest[0][0] == "rule":
        rest = rest[1:]

    # Take the byline from the raw source: the paragraph parser joins its three
    # lines, and they are meant to stack.
    byline_lines = [
        line.strip()
        for line in raw_front_matter.splitlines()
        if line.strip() and not line.startswith("#")
    ]
    meta = " \\\n".join(inline(line) for line in byline_lines)

    return (
        "#align(center)[\n"
        f"  #block(text(size: 20pt, weight: \"bold\")[{inline(title)}])\n"
        "  #v(-2pt)\n"
        f"  #block(width: 88%, text(size: 11.5pt, style: \"italic\")[{inline(subtitle)}])\n"
        "  #v(8pt)\n"
        f"  #block(text(size: 9.2pt)[{meta}])\n"
        "]\n"
        "#v(12pt)\n",
        rest,
    )


def build() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    blocks = parse_blocks(source)
    blocks, figures = extract_figures(blocks)
    front_matter = source.split("\n---\n", 1)[0]
    head, blocks = title_block(front_matter, blocks)

    out = [PREAMBLE, head]
    placed: set[int] = set()
    section = None
    # The executive summary and abstract render inside wrapper blocks. Whichever
    # heading comes next closes the open one, whatever that heading is called —
    # keying this to a specific title silently drops the closer when the paper is
    # restructured, which produces a Typst "unclosed delimiter" far from the cause.
    open_wrapper = False

    for kind, value in blocks:
        if kind == "h":
            level, body = value
            section = body
            if body == "Executive summary":
                out.append(
                    "#block(width: 100%, fill: luma(96%), inset: 11pt, radius: 3pt, "
                    "stroke: 0.4pt + luma(70%))[\n"
                    "#text(size: 11pt, weight: \"bold\")[Executive summary]\n"
                    "#v(3pt)\n#set text(size: 9.2pt)\n"
                )
                open_wrapper = True
                continue
            if body == "Abstract":
                if open_wrapper:
                    out.append("]\n#v(10pt)\n")
                out.append(
                    "#block(width: 100%, inset: (x: 12pt))[\n"
                    "#align(center)[#text(size: 10.5pt, weight: \"bold\")[Abstract]]\n"
                    "#v(2pt)\n#set text(size: 9.4pt)\n"
                )
                open_wrapper = True
                continue
            if open_wrapper:
                out.append("]\n#v(8pt)\n#line(length: 100%, stroke: 0.4pt)\n#v(4pt)\n")
                open_wrapper = False
            out.append(f"{'=' * level} {inline(body)}\n")
            continue

        if kind == "rule":
            out.append("#v(2pt)\n")
            continue

        if kind == "table":
            out.append(emit_table(value))
            continue

        if kind == "list":
            ordered, items = value
            marker = "+" if ordered else "-"
            for item in items:
                out.append(f"{marker} {inline(item)}\n")
            out.append("\n")
            continue

        # Paragraph.
        out.append(inline(value) + "\n\n")

        # Place each figure at the paragraph that first cites it, but not while
        # still inside the front matter or the appendix listing.
        if section not in (None, "Executive summary", "Abstract"):
            for number in sorted(figures):
                if number not in placed and re.search(rf"Figure {number}\b", value):
                    out.append(emit_figure(number, figures[number]))
                    placed.add(number)
                    break

    missing = sorted(set(figures) - placed)
    for number in missing:  # never silently drop a figure
        out.append(emit_figure(number, figures[number]))

    TYP.parent.mkdir(parents=True, exist_ok=True)
    TYP.write_text("".join(out), encoding="utf-8")

    print(f"figures: {len(figures)} found, {len(placed)} placed inline"
          + (f", {len(missing)} appended (no citation found)" if missing else ""))

    # Pin PDF metadata so unchanged sources reproduce byte-for-byte.
    result = subprocess.run(
        [sys.executable, "-c",
         (
             f"import typst; typst.compile({str(TYP)!r}, "
             f"output={str(PDF)!r}, root={str(REPO / 'paper')!r}, "
             f"timestamp={PAPER_BUILD_TIMESTAMP})"
         )],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return 1
    print(f"wrote {PDF.relative_to(REPO)}  ({PDF.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(build())
