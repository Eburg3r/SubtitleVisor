import time
import re
import os
import difflib
import serial
from serial.tools import list_ports

TRANSCRIPT_PATH = r"INSERT_PATH"
BAUD = 115200
FORCE_PORT = "COM3"   # your Pico COM port

# Treat a long period with no NEW words as a new "caption segment"
GAP_RESET_SECONDS = 1.5

# Ignore rapid immediate repeats (whisper jitter)
DUP_SUPPRESS_SECONDS = 0.25

# Diff settings
CONTEXT_MAX_WORDS = 500     # rolling history of words we've already seen
CTX_WINDOW = 180            # only compare against last N words for speed
MIN_MATCH_WORDS = 3         # require at least this many-word overlap to align (lower if needed)

WORD_DELAY_S = 0.0

BRACKET_RE = re.compile(r"\[[^\]]*\]")
ALLOWED_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 !.-:?")

START_AT_END = True
RESYNC_SKIP_SECONDS = 0.35

def find_pico_port():
    if FORCE_PORT:
        return FORCE_PORT
    ports = list(list_ports.comports())
    for p in ports:
        desc = (p.description or "").lower()
        if ("pico" in desc or "raspberry" in desc or "rp2040" in desc or
            "usb" in desc or "cdc" in desc or "usb serial" in desc):
            return p.device
    raise RuntimeError("Could not auto-detect Pico COM port. Set FORCE_PORT.")

def sanitize_line_to_words(line: str):
    # Remove bracket tags + commas + apostrophes, uppercase
    line = BRACKET_RE.sub(" ", line)
    line = line.replace(",", "")
    line = line.replace("’", "").replace("'", "")
    line = line.upper()

    # Keep only allowed chars, map others to space
    cleaned = []
    for ch in line:
        if ch in ALLOWED_CHARS or ch.isspace():
            cleaned.append(ch)
        else:
            cleaned.append(" ")
    cleaned = "".join(cleaned)

    # Split into word-like tokens (punctuation stays attached, e.g. BLUE.)
    return cleaned.split()

def follow_appends(path):
    """
    Yields (chunk, reset_flag).
    Starts at EOF optionally; if file truncates/rewrites, resync to EOF and emit reset_flag.
    """
    offset = 0
    if START_AT_END:
        try:
            offset = os.path.getsize(path)
        except FileNotFoundError:
            offset = 0

    resync_until = 0.0
    pending_reset = False

    while True:
        try:
            size = os.path.getsize(path)
        except FileNotFoundError:
            time.sleep(0.1)
            continue

        if size < offset:
            offset = size
            resync_until = time.time() + RESYNC_SKIP_SECONDS
            pending_reset = True

        if time.time() < resync_until:
            offset = size
            time.sleep(0.05)
            continue

        if pending_reset:
            pending_reset = False
            yield ("", True)

        if size == offset:
            time.sleep(0.03)
            continue

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(offset)
            chunk = f.read(size - offset)
            offset = f.tell()
            if chunk:
                yield (chunk, False)

def compute_new_tail(context_words, line_words):
    """
    Returns only the new words in line_words that appear after the best overlap with context_words.
    Works even when the new line repeats earlier words at the beginning.
    """
    if not line_words:
        return []

    if not context_words:
        return line_words

    ctx = context_words[-CTX_WINDOW:]

    # If the new line is exactly the same as something we've basically already seen, this will return []
    sm = difflib.SequenceMatcher(a=ctx, b=line_words, autojunk=False)

    # Choose the matching block that reaches furthest toward the end of ctx (best "continue from here")
    best_a_end = -1
    best_b_end = 0
    for a0, b0, size in sm.get_matching_blocks():
        if size <= 0:
            continue
        a_end = a0 + size
        b_end = b0 + size
        if size >= max(1, min(MIN_MATCH_WORDS, len(ctx), len(line_words))) and a_end > best_a_end:
            best_a_end = a_end
            best_b_end = b_end

    if best_a_end == -1:
        # No reliable overlap found -> treat whole line as new (rare, but better than stalling forever)
        return line_words

    return line_words[best_b_end:]

def main():
    port = find_pico_port()
    print("Using port:", port)

    # Rolling "already seen" transcript context (used only for diffing)
    context_words = []

    # Output state
    display_is_empty = True
    last_emit_time = None

    # Duplicate suppression
    last_tok = None
    last_tok_time = 0.0

    # Buffer for partial lines
    linebuf = ""

    with serial.Serial(port, BAUD, timeout=0.2) as ser:
        time.sleep(0.5)

        for chunk, reset in follow_appends(TRANSCRIPT_PATH):
            if reset:
                linebuf = ""
                context_words = []
                display_is_empty = True
                last_emit_time = None
                last_tok = None
                last_tok_time = 0.0
                ser.write(b"CLEAR\n")
                ser.flush()
                continue

            # Normalize CR to LF
            chunk = chunk.replace("\r", "\n").replace("\x08", "")
            linebuf += chunk

            # Process complete lines only
            while "\n" in linebuf:
                line, linebuf = linebuf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                line_words = sanitize_line_to_words(line)
                if not line_words:
                    continue

                new_words = compute_new_tail(context_words, line_words)
                if not new_words:
                    continue

                # Update context (rolling)
                context_words.extend(new_words)
                if len(context_words) > CONTEXT_MAX_WORDS:
                    context_words = context_words[-CONTEXT_MAX_WORDS:]

                now = time.time()
                gap = (last_emit_time is None) or ((now - last_emit_time) > GAP_RESET_SECONDS)
                last_emit_time = now

                # If we had a long pause, clear display and start fresh
                if gap:
                    ser.write(b"CLEAR\n")
                    display_is_empty = True

                # Send only the truly new words
                for tok in new_words:
                    now2 = time.time()

                    # suppress only rapid immediate repeats
                    if tok == last_tok and (now2 - last_tok_time) < DUP_SUPPRESS_SECONDS:
                        continue
                    last_tok = tok
                    last_tok_time = now2

                    if display_is_empty:
                        ser.write(f"L:{tok}\n".encode("utf-8"))
                        display_is_empty = False
                    else:
                        ser.write(f"W:{tok}\n".encode("utf-8"))

                    ser.flush()
                    if WORD_DELAY_S:
                        time.sleep(WORD_DELAY_S)

if __name__ == "__main__":
    main()
