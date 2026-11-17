# Remaining Wangdao 408 OCR RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the remaining three scanned Wangdao 2025 textbooks into cleaned, final subject `.txt` files and rebuild the original `primebuddy_408` Chroma collection.

**Architecture:** Reuse the existing local OCRmyPDF preprocessing workflow and the existing `scripts/clean_wangdao_os_ocr.py` conservative text cleaner. Keep `data/408/` as the final RAG input directory with exactly four subject text files and move all PDFs, raw OCR sidecars, and backups to `data/raw/`.

**Tech Stack:** OCRmyPDF, Tesseract `chi_sim+eng`, Python standard library, unittest, existing LangChain/Chroma vector-store loader.

---

## File Structure

- Keep final RAG files in `data/408/`:
  - `data/408/operating_system.txt`
  - `data/408/computer_network.txt`
  - `data/408/computer_organization.txt`
  - `data/408/data_structure.txt`
- Move scanned PDFs from `data/408/` to `data/raw/`:
  - `data/raw/2025王道计算机网络（带书签）.pdf`
  - `data/raw/2025王道计算机组成原理（带书签）.pdf`
  - `data/raw/2025王道数据结构（带书签）.pdf`
- Generate OCR PDFs in `data/raw/`:
  - `data/raw/wangdao_computer_network_2025_ocr.pdf`
  - `data/raw/wangdao_computer_organization_2025_ocr.pdf`
  - `data/raw/wangdao_data_structure_2025_ocr.pdf`
- Generate raw OCR sidecars in `data/raw/`:
  - `data/raw/computer_network_wangdao_2025_ocr_raw.txt`
  - `data/raw/computer_organization_wangdao_2025_ocr_raw.txt`
  - `data/raw/data_structure_wangdao_2025_ocr_raw.txt`
- Back up current short subject summaries in `data/raw/` before overwriting:
  - `data/raw/computer_network_original_summary.txt`
  - `data/raw/computer_organization_original_summary.txt`
  - `data/raw/data_structure_original_summary.txt`
- Modify no app runtime code.
- Keep `config/chroma.yml` collection name as `primebuddy_408`.
- Reset and regenerate `md5.text` for the final four subject files.

No git commits are included because `/Users/sthy/Downloads/PrimeBuddy` is not a git repository.

---

### Task 1: Verify OCR prerequisites and current inputs

**Files:**
- Read-only checks.

- [ ] **Step 1: Verify OCR tools and Tesseract languages**

Run:

```bash
command -v ocrmypdf && command -v tesseract && tesseract --list-langs | grep -E '^(chi_sim|eng)$'
```

Expected: command exits 0 and prints paths plus `chi_sim` and `eng`.

- [ ] **Step 2: Verify three source PDFs and four final subject files exist**

Run:

```bash
python - <<'PY'
from pathlib import Path
required = [
    'data/408/2025王道计算机网络（带书签）.pdf',
    'data/408/2025王道计算机组成原理（带书签）.pdf',
    'data/408/2025王道数据结构（带书签）.pdf',
    'data/408/computer_network.txt',
    'data/408/computer_organization.txt',
    'data/408/data_structure.txt',
    'data/408/operating_system.txt',
]
for name in required:
    p = Path(name)
    print(f'{name}\t{p.exists()}\t{p.stat().st_size if p.exists() else 0}')
    assert p.exists(), name
PY
```

Expected: command exits 0. The three PDFs are tens of MB, and the four subject `.txt` files exist.

---

### Task 2: Move PDFs and back up existing short summaries

**Files:**
- Move: `data/408/2025王道计算机网络（带书签）.pdf` to `data/raw/2025王道计算机网络（带书签）.pdf`
- Move: `data/408/2025王道计算机组成原理（带书签）.pdf` to `data/raw/2025王道计算机组成原理（带书签）.pdf`
- Move: `data/408/2025王道数据结构（带书签）.pdf` to `data/raw/2025王道数据结构（带书签）.pdf`
- Create: `data/raw/computer_network_original_summary.txt`
- Create: `data/raw/computer_organization_original_summary.txt`
- Create: `data/raw/data_structure_original_summary.txt`

- [ ] **Step 1: Back up short summaries and move PDFs**

Run:

```bash
python - <<'PY'
from pathlib import Path
from shutil import copy2, move

raw = Path('data/raw')
raw.mkdir(parents=True, exist_ok=True)

backups = {
    Path('data/408/computer_network.txt'): raw / 'computer_network_original_summary.txt',
    Path('data/408/computer_organization.txt'): raw / 'computer_organization_original_summary.txt',
    Path('data/408/data_structure.txt'): raw / 'data_structure_original_summary.txt',
}
for src, dst in backups.items():
    if not dst.exists():
        copy2(src, dst)
    print(f'backup {src} -> {dst} bytes={dst.stat().st_size}')

pdfs = [
    '2025王道计算机网络（带书签）.pdf',
    '2025王道计算机组成原理（带书签）.pdf',
    '2025王道数据结构（带书签）.pdf',
]
for name in pdfs:
    src = Path('data/408') / name
    dst = raw / name
    if src.exists():
        if dst.exists():
            raise SystemExit(f'target already exists, refusing overwrite: {dst}')
        move(str(src), str(dst))
    print(f'pdf in raw {dst} exists={dst.exists()} bytes={dst.stat().st_size if dst.exists() else 0}')
PY
```

Expected: command exits 0, three backups exist, and three PDFs are now in `data/raw/`.

- [ ] **Step 2: Verify no PDFs remain in final RAG directory**

Run:

```bash
find data/408 -maxdepth 1 -name '*.pdf' -print
```

Expected: no output.

---

### Task 3: OCR the three scanned textbooks

**Files:**
- Create: `data/raw/wangdao_computer_network_2025_ocr.pdf`
- Create: `data/raw/wangdao_computer_organization_2025_ocr.pdf`
- Create: `data/raw/wangdao_data_structure_2025_ocr.pdf`
- Create: `data/raw/computer_network_wangdao_2025_ocr_raw.txt`
- Create: `data/raw/computer_organization_wangdao_2025_ocr_raw.txt`
- Create: `data/raw/data_structure_wangdao_2025_ocr_raw.txt`

- [ ] **Step 1: OCR computer network**

Run:

```bash
ocrmypdf -l chi_sim+eng --deskew --rotate-pages --mode skip --sidecar "data/raw/computer_network_wangdao_2025_ocr_raw.txt" "data/raw/2025王道计算机网络（带书签）.pdf" "data/raw/wangdao_computer_network_2025_ocr.pdf"
```

Expected: OCRmyPDF exits 0 and creates both output files.

- [ ] **Step 2: OCR computer organization**

Run:

```bash
ocrmypdf -l chi_sim+eng --deskew --rotate-pages --mode skip --sidecar "data/raw/computer_organization_wangdao_2025_ocr_raw.txt" "data/raw/2025王道计算机组成原理（带书签）.pdf" "data/raw/wangdao_computer_organization_2025_ocr.pdf"
```

Expected: OCRmyPDF exits 0 and creates both output files.

- [ ] **Step 3: OCR data structure**

Run:

```bash
ocrmypdf -l chi_sim+eng --deskew --rotate-pages --mode skip --sidecar "data/raw/data_structure_wangdao_2025_ocr_raw.txt" "data/raw/2025王道数据结构（带书签）.pdf" "data/raw/wangdao_data_structure_2025_ocr.pdf"
```

Expected: OCRmyPDF exits 0 and creates both output files.

- [ ] **Step 4: Verify sidecar text sizes and previews**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python - <<'PY'
from pathlib import Path
files = [
    'data/raw/computer_network_wangdao_2025_ocr_raw.txt',
    'data/raw/computer_organization_wangdao_2025_ocr_raw.txt',
    'data/raw/data_structure_wangdao_2025_ocr_raw.txt',
]
for name in files:
    p = Path(name)
    text = p.read_text(encoding='utf-8', errors='ignore')
    print(f'{name}\texists={p.exists()}\tchars={len(text)}')
    print(text[:300].replace('\n', ' ')[:300])
    assert p.exists()
    assert len(text) > 100000
PY
```

Expected: all three sidecars exist, each has more than 100000 characters, and previews contain recognizable Chinese textbook text.

---

### Task 4: Clean OCR sidecars into final subject files

**Files:**
- Modify: `data/408/computer_network.txt`
- Modify: `data/408/computer_organization.txt`
- Modify: `data/408/data_structure.txt`

- [ ] **Step 1: Clean all three sidecars into final subject files**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python scripts/clean_wangdao_os_ocr.py --input "data/raw/computer_network_wangdao_2025_ocr_raw.txt" --output "data/408/computer_network.txt" --skip-pages 12 && PYTHONIOENCODING=utf-8 conda run -n agent python scripts/clean_wangdao_os_ocr.py --input "data/raw/computer_organization_wangdao_2025_ocr_raw.txt" --output "data/408/computer_organization.txt" --skip-pages 12 && PYTHONIOENCODING=utf-8 conda run -n agent python scripts/clean_wangdao_os_ocr.py --input "data/raw/data_structure_wangdao_2025_ocr_raw.txt" --output "data/408/data_structure.txt" --skip-pages 12
```

Expected: each cleaner invocation prints `wrote ...` and a character count greater than 100000.

- [ ] **Step 2: Verify final subject text sizes and key terms**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python - <<'PY'
from pathlib import Path
checks = {
    'data/408/computer_network.txt': ['TCP', '拥塞控制', '滑动窗口'],
    'data/408/computer_organization.txt': ['Cache', '流水线', '指令周期'],
    'data/408/data_structure.txt': ['二叉树', 'Dijkstra', '排序'],
    'data/408/operating_system.txt': ['虚拟内存', '进程调度', '死锁'],
}
for name, terms in checks.items():
    text = Path(name).read_text(encoding='utf-8')
    print(f'{name}\tchars={len(text)}')
    assert len(text) > 100000
    found = [term for term in terms if term in text]
    print('found=', found)
    assert found, name
PY
```

Expected: all four final subject files have more than 100000 characters and each has at least one expected subject term.

---

### Task 5: Rebuild original Chroma collection

**Files:**
- Modify: `chroma_db/`
- Modify: `md5.text`

- [ ] **Step 1: Verify `config/chroma.yml` still targets original collection**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -c "from utils.config_handler import chroma_conf; assert chroma_conf['collection_name']=='primebuddy_408'; assert chroma_conf['md5_hex_store']=='md5.text'; assert chroma_conf['k']==5; assert chroma_conf['chunk_size']==700; print(chroma_conf)"
```

Expected: command exits 0 and prints `collection_name: primebuddy_408` in the config dictionary.

- [ ] **Step 2: Reset MD5 ledger and delete original collection**

Run:

```bash
python - <<'PY'
from pathlib import Path
from shutil import copy2
md5 = Path('md5.text')
backup = Path('data/raw/md5_before_all_wangdao_rebuild.text')
if md5.exists() and not backup.exists():
    copy2(md5, backup)
md5.write_text('', encoding='utf-8')
print('md5_reset=True')
PY
PYTHONIOENCODING=utf-8 conda run -n agent python -c 'import chromadb; client=chromadb.PersistentClient(path="chroma_db"); names=[getattr(c,"name",c) for c in client.list_collections()]; print("collections_before=", names); (client.delete_collection("primebuddy_408") if "primebuddy_408" in names else None); print("deleted_collection=", "primebuddy_408" in names); print("collections_after=", [getattr(c,"name",c) for c in client.list_collections()])'
```

Expected: `md5_reset=True`; if `primebuddy_408` existed, it is deleted.

- [ ] **Step 3: Rebuild Chroma using module execution**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m rag.vector_store
```

Expected: command exits 0 and logs successful loading for exactly the four final subject `.txt` files.

- [ ] **Step 4: Verify MD5 ledger contains four final files**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -c "from pathlib import Path; lines=Path('md5.text').read_text(encoding='utf-8').splitlines(); print('md5_lines=', len(lines)); assert len(lines)==4"
```

Expected: `md5_lines= 4`.

---

### Task 6: Validate retrieval, compile, and tests

**Files:**
- No file changes.

- [ ] **Step 1: Verify final `data/408` contains only four `.txt` files**

Run:

```bash
python - <<'PY'
from pathlib import Path
files = sorted(p.name for p in Path('data/408').iterdir() if p.is_file())
print(files)
assert files == ['computer_network.txt', 'computer_organization.txt', 'data_structure.txt', 'operating_system.txt']
PY
```

Expected: exactly the four final `.txt` filenames are printed.

- [ ] **Step 2: Run cross-subject retrieval smoke test**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python - <<'PY'
from rag.vector_store import VectorStoreService
vs = VectorStoreService()
queries = {
    '操作系统 虚拟内存 缺页中断 页面置换': ['虚拟内存', '缺页', '页面'],
    '计算机网络 TCP 拥塞控制 滑动窗口': ['TCP', '拥塞', '窗口'],
    '计算机组成原理 Cache 流水线 指令周期': ['Cache', '流水线', '指令'],
    '数据结构 二叉树 Dijkstra 排序': ['二叉树', 'Dijkstra', '排序'],
}
for query, terms in queries.items():
    docs = vs.get_retriever().invoke(query)
    text = '\n'.join(doc.page_content for doc in docs)
    print('QUERY:', query)
    print('DOCS:', len(docs))
    print(text[:800])
    print('---')
    assert docs
    assert any(term in text for term in terms)
PY
```

Expected: command exits 0 and each subject query retrieves readable subject-specific textbook content.

- [ ] **Step 3: Run Python compile check**

Run:

```bash
PYTHONIOENCODING=utf-8 conda run -n agent python -m compileall app.py agent config model rag utils scripts tests
```

Expected: command exits 0 with no syntax errors.

- [ ] **Step 4: Run cleaner regression tests**

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

- Spec coverage: The plan covers moving three PDFs out of RAG input, backing up original summaries, OCR sidecar generation, cleaning into final subject filenames, rebuilding original `primebuddy_408`, and cross-subject retrieval validation.
- Placeholder scan: No placeholder markers or undefined implementation steps remain.
- Type consistency: The existing cleaner CLI accepts `--input`, `--output`, and `--skip-pages`, and all tasks use those exact flags.
- Scope check: This is a direct repeat of the approved OCR/RAG workflow for the remaining three 408 subjects and does not change app runtime architecture.
