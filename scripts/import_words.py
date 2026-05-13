"""
Import 3742 考研英语单词 into SiYuan.

Creates:
  - Notebook "考研英语"
  - 26 documents (A-Z), each word = a heading block
  - Riff deck "考研单词" for FSRS spaced repetition

Usage:
  python3 scripts/import_words.py [--base-url http://127.0.0.1:6806] [--words-json path/to/words.json]

Requires SiYuan kernel running on 127.0.0.1:6806 with no access auth code set
(localhost auth is auto-bypassed when no auth code is configured).
"""
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── config ──────────────────────────────────────────────────
WORDS_JSON = "/mnt/d/study/kaoyan-english/data/words.json"
SLEEP_BETWEEN_CALLS = 0.05  # 50ms between API calls to avoid overwhelming kernel

CONFIG = {"base_url": "http://127.0.0.1:6806"}

# ── helpers ──────────────────────────────────────────────────

def api(method, path, body=None):
    """Call SiYuan kernel API. All endpoints are POST with JSON body."""
    url = f"{CONFIG['base_url']}{path}"
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"  ✗ HTTP {e.code}: {body}")
        raise
    except urllib.error.URLError as e:
        print(f"  ✗ Connection failed: {e.reason}")
        raise


def word_to_md(w):
    """Convert one word dict to a markdown block group."""
    lines = []

    phonetic = w.get("phonetic", "")
    pos = w.get("pos", "")
    header = f"{w['word']}  {phonetic}  {pos}".strip()
    lines.append(f"## {header}")

    cm = w.get("chinese_meaning", "")
    if cm:
        lines.append(f"\n🇨🇳 {cm}\n")

    em = w.get("english_meaning", "")
    if em:
        lines.append(f"🇬🇧 {em}\n")

    examples = w.get("example_sentences", [])
    if examples:
        lines.append("📝 例句")
        for ex in examples[:3]:
            lines.append(f"> {ex}")
        lines.append("")

    collocations = w.get("collocations", [])
    if collocations:
        lines.append("🔗 搭配")
        for col in collocations[:3]:
            lines.append(f"- {col}")
        lines.append("")

    extra = []
    root = w.get("root_affix", "")
    if root:
        extra.append(f"📐 {root}")
    freq = w.get("exam_frequency", 0)
    if freq:
        extra.append(f"📊 考频: {freq}")
    if extra:
        lines.append(" | ".join(extra))

    return "\n".join(lines)


def build_letter_md(words):
    """Build one giant markdown string for all words in a letter group."""
    parts = []
    for w in words:
        parts.append(word_to_md(w))
        parts.append("\n---\n")
    return "\n".join(parts)


# ── main ─────────────────────────────────────────────────────

def main():
    base_url_arg = CONFIG["base_url"]
    words_json_arg = WORDS_JSON

    # Parse CLI args
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--base-url" and i + 1 < len(args):
            base_url_arg = args[i + 1]; i += 2
        elif args[i] == "--words-json" and i + 1 < len(args):
            words_json_arg = args[i + 1]; i += 2
        else:
            i += 1

    CONFIG["base_url"] = base_url_arg

    # Load words
    print(f"Loading words from {words_json_arg} ...")
    with open(words_json_arg, "r") as f:
        all_words = json.load(f)
    print(f"  {len(all_words)} words loaded")

    # Group by first letter (uppercase)
    groups = {}
    for w in all_words:
        first = w["word"][0].upper()
        if first < "A" or first > "Z":
            first = "A"
        groups.setdefault(first, []).append(w)

    print(f"  Grouped into {len(groups)} letters: {sorted(groups.keys())}")

    # ── Step 1: Create notebook ──
    print("\n── Step 1: Create notebook ──")
    nb_resp = api("POST", "/api/notebook/createNotebook", {"name": "考研英语"})
    if nb_resp.get("code") != 0:
        print(f"  Failed: {nb_resp.get('msg')}")
        sys.exit(1)
    notebook_id = nb_resp["data"]["notebook"]["id"]
    print(f"  Created notebook [考研英语] id={notebook_id}")

    # ── Step 2: Create Riff deck ──
    print("\n── Step 2: Create flashcard deck ──")
    deck_resp = api("POST", "/api/riff/createRiffDeck", {"name": "考研单词"})
    if deck_resp.get("code") != 0:
        print(f"  Failed: {deck_resp.get('msg')}")
        sys.exit(1)
    deck_id = deck_resp["data"]["id"]
    print(f"  Created deck [考研单词] id={deck_id}")

    # ── Step 3: Create letter documents with all word content ──
    print("\n── Step 3: Creating documents (26 letters) ──")
    letter_doc_ids = {}    # letter -> document ID
    all_block_ids = []     # all heading block IDs for Riff registration

    for letter in sorted(groups.keys()):
        words = groups[letter]
        md_content = build_letter_md(words)
        path = f"/{letter}"

        resp = api("POST", "/api/filetree/createDocWithMd", {
            "notebook": notebook_id,
            "path": path,
            "markdown": md_content,
        })

        if resp.get("code") != 0:
            print(f"  [{letter}] Failed: {resp.get('msg')}")
            continue

        doc_id = resp["data"]
        letter_doc_ids[letter] = doc_id
        time.sleep(SLEEP_BETWEEN_CALLS)

        # Get child blocks — heading blocks (type "h") = our word cards
        child_resp = api("POST", "/api/block/getChildBlocks", {"id": doc_id})
        heading_ids = []
        if child_resp.get("code") == 0:
            blocks = child_resp.get("data", [])
            # SiYuan uses short type names: "h"=heading, "p"=paragraph, "b"=blockquote, etc.
            heading_ids = [b["id"] for b in blocks if b.get("type") == "h"]
            all_block_ids.extend(heading_ids)

        print(f"  [{letter}] {len(words):4d} words → doc {doc_id} → {len(heading_ids)} heading blocks")

        time.sleep(SLEEP_BETWEEN_CALLS)

    # ── Step 4: Register heading blocks as Riff cards ──
    print(f"\n── Step 4: Registering {len(all_block_ids)} blocks as flashcards ──")
    BATCH_SIZE = 500
    for batch_start in range(0, len(all_block_ids), BATCH_SIZE):
        batch = all_block_ids[batch_start:batch_start + BATCH_SIZE]
        resp = api("POST", "/api/riff/addRiffCards", {
            "deckID": deck_id,
            "blockIDs": batch,
        })
        if resp.get("code") != 0:
            print(f"  Batch [{batch_start}:{batch_start+BATCH_SIZE}] failed: {resp.get('msg')}")
        else:
            print(f"  Batch [{batch_start}:{batch_start+len(batch)}] registered")
        time.sleep(SLEEP_BETWEEN_CALLS)

    # ── Done ──
    print(f"\n{'='*60}")
    print(f"Import complete!")
    print(f"  Notebook: 考研英语 ({notebook_id})")
    print(f"  Documents: {len(letter_doc_ids)} letters")
    print(f"  Words:     {len(all_block_ids)} cards in deck [考研单词] ({deck_id})")
    print(f"\nOpen http://127.0.0.1:6806/stage/build/desktop/ to review.")
    print(f"Card review: right-click a block → 'Make Flashcard' is already done.")
    print(f"Or use the built-in flashcard review UI.")


if __name__ == "__main__":
    main()
