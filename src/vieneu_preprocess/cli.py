"""`vieneu-preprocess` command line: one chapter file or a directory of chapters.

    vieneu-preprocess INPUT [--out DIR] [--format script|json|both] [--dict FILE ...]
                      [--rules FILE] [--render --voice NAME]

INPUT is a `.md`, `.txt` or `.html` file, or a directory (every such file in it,
one output set per chapter, numbered in name order). Outputs default to a
`preprocessed/` folder next to the input.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, Sequence

from .dictionary_schema import DictionaryFormatError, load_dictionary_json, merge_lexicon
from .exporters import to_json_text
from .html_to_text import html_to_text
from .pipeline import run_pipeline
from .rules import RulesError, load_rules
from .types import LexiconEntry

INPUT_SUFFIXES = (".md", ".txt", ".html", ".htm")
OUTPUT_MARKERS = (".script.txt",)
log = logging.getLogger("vieneu_preprocess.cli")


def collect_inputs(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(p for p in path.iterdir()
                      if p.is_file() and p.suffix.lower() in INPUT_SUFFIXES
                      and not p.name.endswith(OUTPUT_MARKERS))
    raise FileNotFoundError(f"input not found: {path}")


def read_chapter(path: Path) -> str:
    text = path.read_text(encoding="utf-8-sig")
    return html_to_text(text) if path.suffix.lower() in (".html", ".htm") else text


def load_lexicon(files: Sequence[str]) -> list[LexiconEntry]:
    dicts = []
    for f in files:
        try:
            dicts.append(load_dictionary_json(Path(f).read_bytes()))
        except DictionaryFormatError as e:
            raise SystemExit(f"error: dictionary {f}: {e}") from e
        except OSError as e:
            raise SystemExit(f"error: cannot read dictionary {f}: {e}") from e
    return merge_lexicon(dicts)


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="vieneu-preprocess",
                                 description="Story preprocessor (tts-specs-v1) for VieNeu-TTS.")
    ap.add_argument("input", help="chapter file (.md/.txt/.html) or a directory of chapters")
    ap.add_argument("--out", help="output directory (default: <input dir>/preprocessed)")
    ap.add_argument("--format", choices=("script", "json", "both"), default="both")
    ap.add_argument("--dict", nargs="+", default=[], metavar="FILE",
                    help="vieneu-dictionary/1 JSON files merged into the lexicon")
    ap.add_argument("--rules", help="YAML deep-merged over the default pause rules")
    ap.add_argument("--render", action="store_true", help="also synthesize a 48 kHz WAV per chapter")
    ap.add_argument("--voice", help="voice for chunks without a voice (with --render)")
    return ap


def _load_engine():
    from vieneu import Vieneu  # heavy import only when rendering

    return Vieneu()


def main(argv: Optional[Sequence[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _build_parser().parse_args(argv)
    src = Path(args.input)
    try:
        inputs = collect_inputs(src)
        rules = load_rules(args.rules)
    except (FileNotFoundError, RulesError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not inputs:
        print(f"error: no {', '.join(INPUT_SUFFIXES)} files in {src}", file=sys.stderr)
        return 2
    lexicon = load_lexicon(args.dict)
    out_dir = Path(args.out) if args.out else (src if src.is_dir() else src.parent) / "preprocessed"
    out_dir.mkdir(parents=True, exist_ok=True)
    tts = _load_engine() if args.render else None
    for number, path in enumerate(inputs, start=1):
        try:
            result = run_pipeline(read_chapter(path), lexicon, rules=rules, chapter=number)
        except (OSError, UnicodeDecodeError) as e:
            print(f"error: {path}: {e}", file=sys.stderr)
            return 1
        if args.format in ("script", "both"):
            (out_dir / f"{path.stem}.script.txt").write_text(result.script, encoding="utf-8")
        if args.format in ("json", "both"):
            (out_dir / f"{path.stem}.json").write_text(to_json_text(result), encoding="utf-8")
        if tts is not None:
            import soundfile as sf

            from .runner import SAMPLE_RATE, render_chunks

            wav = render_chunks(result.chunks, tts, default_voice=args.voice)
            sf.write(str(out_dir / f"{path.stem}.wav"), wav, SAMPLE_RATE)
        log.info("%s -> %s (%d chunks)", path.name, out_dir, len(result.chunks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
