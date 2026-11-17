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
    parser.add_argument("--source-name", default=SOURCE_NAME, help="Source name used in page markers.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    raw_text = input_path.read_text(encoding="utf-8", errors="ignore")
    cleaned = clean_text(raw_text, skip_pages=args.skip_pages, source_name=args.source_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(cleaned, encoding="utf-8")
    print(f"wrote {output_path} ({len(cleaned)} chars)")


if __name__ == "__main__":
    main()
