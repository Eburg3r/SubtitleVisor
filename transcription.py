import re
import subprocess
from pathlib import Path

REPO = Path(r"INSERT_PATH")
EXE = REPO / r"build\bin\Release\whisper-stream.exe"
MODEL = REPO / r"models\ggml-base.en.bin"

OUT_LOG = REPO / "transcript.txt"   # append-only: one new line per new chunk
OUT_LIVE = REPO / "live.txt"        # optional: overwrite with latest full text

CAPTURE = "0"
THREADS = "256"

# VAD settings
LENGTH_MS = "15000"
VAD_THOLD = "0.7"   # raise if silence still triggers; lower if it misses quiet speech

# --- parsing helpers ---
ts_prefix = re.compile(r"^\[[^\]]+\]\s*")          # strips "[.. --> ..] "
word_re = re.compile(r"[A-Za-z0-9']+")             # "words" for overlap matching

# NEW: remove anything inside [...] or (...)
BRACKETED_RE = re.compile(r"\[[^\]]*\]")
PAREN_RE = re.compile(r"\([^)]*\)")


def normalize_text(s: str) -> str:
    s = s.strip()

    # NEW: remove bracketed/parenthetical stage directions like "[typing sounds]" or "(music)"
    s = BRACKETED_RE.sub("", s)
    s = PAREN_RE.sub("", s)

    # normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def words(s: str) -> list[str]:
    return word_re.findall(s)


def new_words_delta(committed: list[str], candidate: list[str]) -> list[str]:
    """
    Return only the new words that candidate adds beyond what we've already committed.
    Handles:
      - candidate starts with all committed words
      - candidate starts with a suffix of committed words (sliding window overlap)
    """
    if not candidate:
        return []

    # Best case: candidate begins with entire committed transcript
    if len(committed) <= len(candidate) and candidate[: len(committed)] == committed:
        return candidate[len(committed):]

    # Otherwise, find the longest overlap where a suffix of committed == prefix of candidate
    max_k = min(len(committed), len(candidate))
    for k in range(max_k, 0, -1):
        if committed[-k:] == candidate[:k]:
            return candidate[k:]

    # No overlap found: treat whole candidate as new (e.g., after a hard reset)
    return candidate


cmd = [
    str(EXE),
    "--capture", CAPTURE,
    "--model", str(MODEL),
    "-t", THREADS,
    "--step", "0",              # VAD mode
    "--length", LENGTH_MS,
    "-vth", VAD_THOLD,
    # IMPORTANT: no --file
]

# Start fresh (optional)
OUT_LOG.write_text("", encoding="utf-8")
OUT_LIVE.write_text("", encoding="utf-8")

p = subprocess.Popen(
    cmd,
    cwd=str(REPO),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

in_block = False
block_lines: list[str] = []
committed_words: list[str] = []

with OUT_LOG.open("a", encoding="utf-8") as log:
    for line in p.stdout:
        line = line.rstrip("\r\n")

        if line.startswith("### Transcription") and "START" in line:
            in_block = True
            block_lines = []
            continue

        if line.startswith("### Transcription") and "END" in line:
            in_block = False

            block_text = normalize_text(" ".join(block_lines))
            cand_words = words(block_text)

            delta = new_words_delta(committed_words, cand_words)
            delta_text = normalize_text(" ".join(delta))

            if delta_text:
                # Append ONLY new words as a new line
                log.write(delta_text + "\n")
                log.flush()

                # Update the committed transcript
                committed_words.extend(delta)

                # Optional: write "full current transcript" for overlays
                OUT_LIVE.write_text(" ".join(committed_words), encoding="utf-8")

            continue

        if not in_block:
            continue

        # Inside VAD block: strip timestamps and keep only text content
        line = ts_prefix.sub("", line).strip()
        if line:
            block_lines.append(line)
