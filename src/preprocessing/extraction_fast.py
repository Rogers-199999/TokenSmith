from pathlib import Path
import re
import json
from typing import List, Dict
import sys

from pypdf import PdfReader


def extract_sections_from_markdown(
    file_path: str,
    exclusion_keywords: List[str] = None
) -> List[Dict]:
    """
    Chunks a markdown file into sections based on '##' headings.

    Args:
        file_path : The path to the markdown file.
        exclusion_keywords : List of keywords for excluding sections.

    Returns:
        list: A list of dictionaries, where each dictionary represents a
              section with 'heading' and 'content' keys.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

    heading_pattern = r'(?=^## \d+(\.\d+)* .*)'
    numbering_pattern = re.compile(r"(\d+(?:\.\d+)*)")
    chunks = re.split(heading_pattern, content, flags=re.MULTILINE)

    sections = []

    if chunks and chunks[0].strip():
        sections.append({
            'heading': 'Introduction',
            'content': preprocess_extracted_section(chunks[0].strip()),
            'level': 1,
            'chapter': 0
        })

    for chunk in chunks[1:]:
        if not chunk or not chunk.strip():
            continue

        parts = chunk.split('\n', 1)
        heading = parts[0].strip()
        heading = heading.lstrip('#').strip()
        heading = f"Section {heading}"

        if exclusion_keywords is not None:
            if any(keyword.lower() in heading.lower() for keyword in exclusion_keywords):
                continue

        section_content = parts[1].strip() if len(parts) > 1 else ''
        if not section_content:
            continue

        section_content = preprocess_extracted_section(section_content)

        match = numbering_pattern.search(heading)
        if match:
            section_number = match.group(1)
            current_level = section_number.count('.') + 1
            try:
                chapter_num = int(section_number.split('.')[0])
            except ValueError:
                chapter_num = 0
        else:
            current_level = 1
            chapter_num = 0

        sections.append({
            'heading': heading,
            'content': section_content,
            'level': current_level,
            'chapter': chapter_num
        })

    return sections

def extract_chunks_from_fast_markdown(
    file_path: str,
    max_chars: int = 1200,
    overlap: int = 150
) -> List[Dict]:
    """
    Extract chunks from fast-extracted markdown by splitting on page markers,
    then further splitting long page text into overlapping character chunks.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by page markers like --- Page 12 ---
    pattern = re.compile(r"\n\s*--- Page (\d+) ---\s*\n")
    parts = pattern.split(content)

    sections = []

    # parts format:
    # [text_before_first_marker, page_num_1, text_1, page_num_2, text_2, ...]
    if len(parts) < 3:
        return sections

    for i in range(1, len(parts), 2):
        page_num = int(parts[i])
        page_text = parts[i + 1].strip()

        if not page_text:
            continue

        # split long page text into overlapping chunks
        start = 0
        chunk_id = 0
        while start < len(page_text):
            end = min(start + max_chars, len(page_text))
            chunk_text = page_text[start:end].strip()

            if chunk_text:
                sections.append({
                    "heading": f"Page {page_num} Chunk {chunk_id}",
                    "content": chunk_text,
                    "level": 1,
                    "chapter": 0,
                    "page": page_num
                })

            if end == len(page_text):
                break

            start += max_chars - overlap
            chunk_id += 1

    return sections


def preprocess_extracted_section(text: str) -> str:
    """
    Cleans raw textbook section text to prepare it for chunking.
    """
    text = text.replace('\n', ' ')
    text = text.replace('<!-- image -->', ' ')
    text = text.replace('**', ' ')
    cleaned_text = ' '.join(text.split())
    return cleaned_text


def clean_page_text(text: str) -> str:
    """
    Lightweight cleanup for page-level extracted text.

    This keeps the extractor fast and avoids overly aggressive cleanup.
    """
    if not text:
        return ""

    # normalize common unicode whitespace / hyphen oddities
    text = text.replace('\x00', ' ')
    text = text.replace('\u00ad', '')   # soft hyphen
    text = text.replace('\uf0b7', ' ')  # bullet-like artifacts sometimes seen
    text = text.replace('\r', '\n')

    # collapse excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # trim trailing spaces per line
    text = '\n'.join(line.rstrip() for line in text.splitlines())

    return text.strip()


def fast_extract_pdf_to_markdown(
    input_file_path: str,
    output_file_path: str,
    start_page: int = None,
    end_page: int = None,
    skip_empty_pages: bool = False
) -> None:
    """
    Fast PDF-to-markdown extraction using pypdf text extraction only.

    Args:
        input_file_path: source PDF path
        output_file_path: destination markdown path
        start_page: 1-based start page (inclusive), default = first page
        end_page: 1-based end page (inclusive), default = last page
        skip_empty_pages: if True, pages with no extracted text are skipped
    """
    source = Path(input_file_path)
    if not source.exists():
        print(f"Error: Input file not found at {input_file_path}", file=sys.stderr)
        return

    try:
        reader = PdfReader(str(source))
    except Exception as e:
        print(f"Error opening PDF {input_file_path}: {e}", file=sys.stderr)
        return

    total_pages = len(reader.pages)
    if total_pages == 0:
        print(f"Error: PDF has no pages: {input_file_path}", file=sys.stderr)
        return

    if start_page is None:
        start_page = 1
    if end_page is None:
        end_page = total_pages

    start_page = max(1, start_page)
    end_page = min(total_pages, end_page)

    if start_page > end_page:
        print(
            f"Error: invalid page range start_page={start_page}, end_page={end_page}",
            file=sys.stderr
        )
        return

    parts = []

    print(
        f"Fast extracting pages {start_page}-{end_page} from '{input_file_path}' "
        f"to '{output_file_path}'..."
    )

    for page_num in range(start_page, end_page + 1):
        try:
            page = reader.pages[page_num - 1]
            text = page.extract_text() or ""
            text = clean_page_text(text)
        except Exception as e:
            print(f"Warning: failed to extract page {page_num}: {e}", file=sys.stderr)
            text = ""

        if skip_empty_pages and not text:
            continue

        # add page content
        if text:
            parts.append(text)
        else:
            parts.append(f"[No extractable text on page {page_num}]")

        # add page marker
        parts.append(f"\n\n--- Page {page_num} ---\n\n")

    final_text = "".join(parts)

    try:
        Path(output_file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(final_text)
        print(f"Successfully saved fast extraction to {output_file_path}")
    except Exception as e:
        print(f"Error writing to file {output_file_path}: {e}", file=sys.stderr)


def main():
    """
    Fast extraction entry point.

    By default:
    - scans data/chapters/*.pdf
    - extracts each PDF into data/<name>--extracted_markdown.md
    - then runs section extraction on the first markdown file
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    chapters_dir = project_root / "data" / "chapters"
    pdfs = sorted(chapters_dir.glob("*.pdf"))

    if len(pdfs) == 0:
        print("ERROR: No PDFs found in data/chapters/. Please copy a PDF there first.", file=sys.stderr)
        sys.exit(1)

    markdown_files = []

    for pdf_path in pdfs:
        pdf_name = pdf_path.stem
        output_md = project_root / "data" / f"{pdf_name}--extracted_markdown.md"

        print(f"Converting '{pdf_path}' to '{output_md}' using fast extraction...")
        fast_extract_pdf_to_markdown(
            input_file_path=str(pdf_path),
            output_file_path=str(output_md),
            start_page=None,
            end_page=None,
            skip_empty_pages=False
        )

        markdown_files.append(output_md)

    # Keep the downstream behavior similar to extraction.py
    # extracted_sections = extract_sections_from_markdown(str(markdown_files[0]))
    extracted_sections = extract_chunks_from_fast_markdown(str(markdown_files[0]), max_chars=1200, overlap=150)

    if extracted_sections:
        print(f"Successfully extracted {len(extracted_sections)} sections.")
        output_filename = project_root / "data" / "extracted_sections.json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(extracted_sections, f, indent=4, ensure_ascii=False)
        print(f"Full extracted content saved to '{output_filename}'")
    else:
        print("Warning: No sections were extracted. The markdown may not contain expected '##' headings.")


if __name__ == '__main__':
    main()