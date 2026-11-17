# Wangdao OS OCR RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the scanned Wangdao 2025 operating system PDF into cleaned, RAG-ready text and ingest it into PrimeBuddy's Chroma knowledge base.

**Architecture:** Keep OCR as a local command-line preprocessing step and keep the app's existing RAG loader unchanged. Add one focused cleaner script that converts OCRmyPDF sidecar text into structured `.txt`, then point Chroma at a new collection and MD5 store so the rebuild is non-destructive.

**Tech Stack:** OCRmyPDF, Tesseract `chi_sim+eng`, Python standard library, unittest, Streamlit/LangChain/Chroma existing project code.

---

## File Structure

- Create `scripts/clean_wangdao_os_ocr.py`: cleans OCRmyPDF sidecar text into a structured RAG text file.
- Create `tests/test_clean_wangdao_os_ocr.py`: verifies front-matter skipping, page source markers, page-number removal, and Chinese line merging.
- Modify `config/chroma.yml`: switch to a non-destructive v2 collection and tune chunking for long textbook content.
- Move `data/408/2025王道操作系统（带书签）.pdf` to `data/raw/2025王道操作系统（带书签）.pdf`: keep scanned image PDF out of the RAG scan directory.
- Generate `data/408/operating_system_wangdao_2025_ocr_raw.txt`: OCRmyPDF sidecar text.
- Generate `data/408/operating_system_wangdao_2025_ocr.txt`: cleaned RAG-ready text.
- Generate `data/raw/wangdao_os_2025_ocr.pdf`: searchable OCR PDF for manual inspection.
- Create `md5_wangdao_v2.text`: new MD5 ledger used by the v2 collection.

No git commits are included because `/Users/sthy/Downloads/PrimeBuddy` is not a git repository.

---

### Task 1: Verify local OCR toolchain

**Files:**
- No file changes.

- [ ] **Step 1: Check command availability**

Run:

```bash
command -v ocrmypdf && command -v tesseract && command -v python && command -v conda
```

Expected if installed: four absolute paths are printed, including paths ending in `ocrmypdf` and `tesseract`.

Expected if missing: the command exits non-zero and stops printing before all four tools appear.

- [ ] **Step 2: Install missing macOS OCR tools if Step 1 fails**

Run only if a tool is missing:

```bash
brew install ocrmypdf tesseract tesseract-lang poppler
```

Expected: Homebrew finishes with no `Error:` lines and `ocrmypdf`, `tesseract`, and Poppler tools are installed.

- [ ] **Step 3: Verify Chinese and English OCR languages**

Run:

```bash
tesseract --list-langs | grep -E '^(chi_sim|eng)$'
```

Expected:

```text
chi_sim
eng
```

If `chi_sim` is missing after `brew install tesseract-lang`, stop and install the Simplified Chinese Tesseract language data before running OCR.

---

### Task 2: Add OCR text cleaner with tests

**Files:**
- Create: `scripts/clean_wangdao_os_ocr.py`
- Create: `tests/test_clean_wangdao_os_ocr.py`

- [ ] **Step 1: Create script and test directories**

Run:

```bash
mkdir -p scripts tests
```

Expected: command exits 0.

- [ ] **Step 2: Write the failing cleaner tests**

Create `tests/test_clean_wangdao_os_ocr.py` with this content:

```python
import unittest

from scripts.clean_wangdao_os_ocr import clean_text


class CleanWangdaoOsOcrTest(unittest.TestCase):
    def test_skips_front_matter_and_adds_page_source_markers(self):
        raw_text = "\f".join(
            [
                "扉页\n1\n",
                "目 录\n2\n",
                "第1章   计算机系统概述\n1.1   操作系统的基本概念\n操作系统是指控制和管理\n整个计算机系统的硬件和软件资源。\n13\n",
            ]
        )

        cleaned = clean_text(raw_text, skip_pages=2, source_name="2025王道操作系统")

        self.assertNotIn("扉页", cleaned)
        self.assertNotIn("目 录", cleaned)
        self.assertIn("[来源：2025王道操作系统，第 3 页]", cleaned)
        self.assertIn("第1章 计算机系统概述", cleaned)
        self.assertIn("1.1 操作系统的基本概念", cleaned)
        self.assertIn("操作系统是指控制和管理整个计算机系统的硬件和软件资源。", cleaned)
        self.assertNotIn("\n13\n", cleaned)

    def test_keeps_exercise_and_answer_sections(self):
        raw_text = "\f".join(
            [
                "封面\n",
                "本节习题精选\n下列关于操作系统的说法\n正确的是（ ）。\n14\n",
                "答案与解析\n本题考查操作系统的目标和功能。\n15\n",
            ]
        )

        cleaned = clean_text(raw_text, skip_pages=1, source_name="2025王道操作系统")

        self.assertIn("本节习题精选", cleaned)
        self.assertIn("下列关于操作系统的说法正确的是（ ）。", cleaned)
        self.assertIn("答案与解析", cleaned)
        self.assertIn("本题考查操作系统的目标和功能。", cleaned)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail before implementation**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest tests.test_clean_wangdao_os_ocr -v
```

Expected: FAIL or ERROR because `scripts.clean_wangdao_os_ocr` does not exist yet.

- [ ] **Step 4: Write the cleaner implementation**

Create `scripts/clean_wangdao_os_ocr.py` with this content:

```python
from __future__ import annotations

import argparse
import re
from pathlib import Path

SOURCE_NAME = "2025王道操作系统"

HEADING_PATTERNS = [
    re.compile(r"^第[一二三四五六七八九十0-9]+章\s+"),
    re.compile(r"^\d+(?:\.\d+){1,3}\s+"),
    re.compile(r"^(本节习题精选|答案与解析)$"),
    re.compile(r"^例题\s*\d*"),
]

NOISE_PATTERNS = [
    re.compile(r"^\d+$"),
    re.compile(r"^[-—_\s]+$"),
    re.compile(r"^第\s*\d+\s*页$"),
    re.compile(r"^\s*$"),
    re.compile(r".*资源兑换.*"),
    re.compile(r".*扫码.*"),
    re.compile(r".*微信公众号.*"),
    re.compile(r".*王道论坛.*"),
]

END_PUNCTUATION = tuple("。！？；;：:，,、）)]】》”’\"'")
START_SEPARATE_PATTERNS = [
    re.compile(r"^第[一二三四五六七八九十0-9]+章"),
    re.compile(r"^\d+(?:\.\d+){1,3}\s+"),
    re.compile(r"^[(（]?\d+[)）.]"),
    re.compile(r"^[A-D][.．、]"),
    re.compile(r"^(本节习题精选|答案与解析|例题)"),
]


def normalize_line(line: str) -> str:
    line = line.replace("　", " ").replace("\xa0", " ").replace("​", "")
    line = re.sub(r"[ \t]+", " ", line)
    line = line.strip()
    line = re.sub(r"^(第[一二三四五六七八九十0-9]+章)\s*", r"\1 ", line)
    line = re.sub(r"^(\d+(?:\.\d+){1,3})\s*", r"\1 ", line)
    return line


def is_heading(line: str) -> bool:
    return any(pattern.search(line) for pattern in HEADING_PATTERNS)


def is_noise_line(line: str) -> bool:
    return any(pattern.search(line) for pattern in NOISE_PATTERNS)


def starts_separate_block(line: str) -> bool:
    return any(pattern.search(line) for pattern in START_SEPARATE_PATTERNS)


def should_join(previous: str, current: str) -> bool:
    if not previous or not current:
        return False
    if is_heading(previous) or is_heading(current):
        return False
    if previous.endswith(END_PUNCTUATION):
        return False
    if starts_separate_block(current):
        return False
    return True


def clean_page(page_text: str) -> list[str]:
    cleaned_lines: list[str] = []
    for raw_line in page_text.splitlines():
        line = normalize_line(raw_line)
        if is_noise_line(line):
            continue
        if cleaned_lines and should_join(cleaned_lines[-1], line):
            cleaned_lines[-1] += line
        else:
            cleaned_lines.append(line)
    return cleaned_lines


def clean_text(raw_text: str, skip_pages: int = 12, source_name: str = SOURCE_NAME) -> str:
    pages = re.split(r"\f+", raw_text)
    output: list[str] = []

    for page_number, page_text in enumerate(pages, start=1):
        if page_number <= skip_pages:
            continue
        lines = clean_page(page_text)
        if not lines:
            continue
        output.append(f"[来源：{source_name}，第 {page_number} 页]")
        output.extend(lines)
        output.append("")

    return "\n".join(output).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean Wangdao OS OCR sidecar text for PrimeBuddy RAG ingestion.")
    parser.add_argument("--input", required=True, help="Path to OCRmyPDF sidecar text file.")
    parser.add_argument("--output", required=True, help="Path to cleaned RAG-ready text file.")
    parser.add_argument("--skip-pages", type=int, default=12, help="Number of front-matter PDF pages to skip.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    raw_text = input_path.read_text(encoding="utf-8", errors="ignore")
    cleaned = clean_text(raw_text, skip_pages=args.skip_pages)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(cleaned, encoding="utf-8")
    print(f"wrote {output_path} ({len(cleaned)} chars)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify cleaner passes**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest tests.test_clean_wangdao_os_ocr -v
```

Expected:

```text
Ran 2 tests
OK
```

---

### Task 3: Run OCRmyPDF and create sidecar text

**Files:**
- Move: `data/408/2025王道操作系统（带书签）.pdf` to `data/raw/2025王道操作系统（带书签）.pdf`
- Create: `data/raw/wangdao_os_2025_ocr.pdf`
- Create: `data/408/operating_system_wangdao_2025_ocr_raw.txt`

- [ ] **Step 1: Create raw data directory**

Run:

```bash
mkdir -p data/raw
```

Expected: command exits 0.

- [ ] **Step 2: Move scanned PDF out of the RAG scan directory**

Run:

```bash
mv "data/408/2025王道操作系统（带书签）.pdf" "data/raw/2025王道操作系统（带书签）.pdf"
```

Expected: command exits 0.

- [ ] **Step 3: Verify the PDF moved**

Run:

```bash
test -f "data/raw/2025王道操作系统（带书签）.pdf" && test ! -f "data/408/2025王道操作系统（带书签）.pdf"
```

Expected: command exits 0.

- [ ] **Step 4: Run OCRmyPDF with Chinese and English languages**

Run:

```bash
ocrmypdf -l chi_sim+eng --deskew --rotate-pages --mode skip --sidecar "data/408/operating_system_wangdao_2025_ocr_raw.txt" "data/raw/2025王道操作系统（带书签）.pdf" "data/raw/wangdao_os_2025_ocr.pdf"
```

Expected: OCRmyPDF exits 0 and creates both output files. This can take a long time for 368 pages.

- [ ] **Step 5: Verify OCR output files exist and raw sidecar has text**

Run:

```bash
conda run -n agent python -c "from pathlib import Path; raw=Path('data/408/operating_system_wangdao_2025_ocr_raw.txt'); pdf=Path('data/raw/wangdao_os_2025_ocr.pdf'); text=raw.read_text(encoding='utf-8', errors='ignore'); print('raw_exists=', raw.exists()); print('ocr_pdf_exists=', pdf.exists()); print('raw_chars=', len(text)); print(text[:500])"
```

Expected:

```text
raw_exists= True
ocr_pdf_exists= True
raw_chars= <a number greater than 100000>
```

The preview should contain recognizable Chinese operating system content. If it is mostly symbols or empty whitespace, stop and inspect OCR language installation.

---

### Task 4: Clean OCR sidecar text

**Files:**
- Create: `data/408/operating_system_wangdao_2025_ocr.txt`

- [ ] **Step 1: Run cleaner on OCR sidecar text**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python scripts/clean_wangdao_os_ocr.py --input "data/408/operating_system_wangdao_2025_ocr_raw.txt" --output "data/408/operating_system_wangdao_2025_ocr.txt" --skip-pages 12
```

Expected: output includes `wrote data/408/operating_system_wangdao_2025_ocr.txt` and a character count greater than `100000`.

- [ ] **Step 2: Inspect cleaned text quality around known OS terms**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -c "from pathlib import Path; text=Path('data/408/operating_system_wangdao_2025_ocr.txt').read_text(encoding='utf-8'); print('chars=', len(text));\nfor term in ['进程调度', '虚拟内存', '死锁', '文件系统', '磁盘调度']:\n    i=text.find(term); print('TERM', term, 'INDEX', i); print(text[max(0, i-120):i+220] if i >= 0 else 'NOT FOUND'); print('---')"
```

Expected: at least four of the five terms have non-negative indexes and their previews contain readable Chinese sentences.

- [ ] **Step 3: Count source markers**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -c "from pathlib import Path; text=Path('data/408/operating_system_wangdao_2025_ocr.txt').read_text(encoding='utf-8'); print(text.count('[来源：2025王道操作系统'))"
```

Expected: a number close to `356`, because the first 12 front-matter pages are skipped from a 368-page PDF and pages with no OCR text are omitted.

---

### Task 5: Tune Chroma config for textbook ingestion

**Files:**
- Modify: `config/chroma.yml`

- [ ] **Step 1: Update Chroma collection, MD5 ledger, retrieval count, and chunking**

Edit `config/chroma.yml` to exactly this content:

```yaml
collection_name: primebuddy_408_wangdao_v2
persist_directory: chroma_db
k: 5
data_path: data/408
md5_hex_store: md5_wangdao_v2.text
allow_knowledge_file_type: ["txt", "pdf"]

chunk_size: 700
chunk_overlap: 100
separators: ["\n\n", "\n", ".", "!", "?", "。", "！", "？", " ", ""]
```

- [ ] **Step 2: Verify config parses**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -c "from utils.config_handler import chroma_conf; assert chroma_conf['collection_name']=='primebuddy_408_wangdao_v2'; assert chroma_conf['md5_hex_store']=='md5_wangdao_v2.text'; assert chroma_conf['k']==5; assert chroma_conf['chunk_size']==700; assert chroma_conf['chunk_overlap']==100; print(chroma_conf)"
```

Expected: command exits 0 and prints the parsed config dictionary.

---

### Task 6: Build the v2 vector store

**Files:**
- Create: `md5_wangdao_v2.text`
- Modify: `chroma_db/`

- [ ] **Step 1: Ensure the scanned PDF is not in `data/408`**

Run:

```bash
find data/408 -maxdepth 1 -name '*.pdf' -print
```

Expected: no output. If a PDF path is printed, move it to `data/raw/` before continuing.

- [ ] **Step 2: Build the Chroma collection**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python rag/vector_store.py
```

Expected: command exits 0. Console/log output should include successful knowledge-base loading entries for `.txt` files, including `operating_system_wangdao_2025_ocr.txt`.

- [ ] **Step 3: Verify the new MD5 ledger exists and is populated**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -c "from pathlib import Path; p=Path('md5_wangdao_v2.text'); lines=p.read_text(encoding='utf-8').splitlines(); print('exists=', p.exists()); print('lines=', len(lines)); assert p.exists(); assert len(lines) >= 5"
```

Expected: `exists= True` and `lines=` at least `5`, covering the existing four 408 text files plus the cleaned OCR text file.

---

### Task 7: Validate RAG retrieval quality

**Files:**
- No file changes.

- [ ] **Step 1: Run retrieval smoke test for core OS topics**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -c "from rag.vector_store import VectorStoreService; vs=VectorStoreService(); queries=['进程调度 时间片轮转 优先级调度','虚拟内存 缺页中断 页面置换','死锁 必要条件 银行家算法','文件系统 索引分配 FAT','磁盘调度 SCAN C-SCAN'];\nfor q in queries:\n    docs=vs.get_retriever().invoke(q); text='\n'.join(d.page_content for d in docs); print('QUERY:', q); print('DOCS:', len(docs)); print(text[:800]); print('---'); assert docs; assert any(term in text for term in q.split())"
```

Expected: command exits 0. Each query prints `DOCS:` greater than `0` and readable operating-system text.

- [ ] **Step 2: Run compile check after adding the cleaner script**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m compileall app.py agent config model rag utils scripts tests
```

Expected: command exits 0 with no syntax errors.

- [ ] **Step 3: Run cleaner tests again**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m unittest tests.test_clean_wangdao_os_ocr -v
```

Expected:

```text
Ran 2 tests
OK
```

---

## Self-Review Notes

- Spec coverage: The plan covers toolchain verification, scanned PDF relocation, OCR sidecar generation, text cleaning, non-destructive Chroma config, ingestion, and retrieval verification.
- Placeholder scan: No placeholder markers or undefined implementation steps remain.
- Type consistency: The cleaner exposes `clean_text(raw_text: str, skip_pages: int, source_name: str) -> str`, which matches the tests and CLI implementation.
- Scope check: This remains one focused pipeline for one scanned operating-system PDF; it does not change PrimeBuddy's Agent or RAG runtime architecture.
