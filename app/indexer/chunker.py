"""RFC document parsing and chunking."""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DocumentChunk:
    """Represents a chunk of an RFC document."""

    id: str
    rfc_id: str
    rfc_number: str
    rfc_title: str
    wg: str
    section_number: str
    section_title: str
    text: str
    chunk_index: int

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


class RFCChunker:
    """Section-aware chunker tailored for standard IETF RFC documents."""

    def __init__(
        self,
        metadata_file: Path,
        max_chunk_chars: int = 1500,
        chunk_overlap_chars: int = 200,
    ) -> None:
        self.metadata_file = metadata_file
        self.max_chunk_chars = max_chunk_chars
        self.chunk_overlap_chars = chunk_overlap_chars
        self.metadata_map: Dict[str, Dict[str, str]] = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Dict[str, str]]:
        if not self.metadata_file.exists():
            return {}
        try:
            items = json.loads(self.metadata_file.read_text(encoding="utf-8"))
            return {item["rfc_id"].lower(): item for item in items}
        except Exception:
            return {}

    def _clean_rfc_text(self, raw_text: str) -> str:
        """Strip form feeds, page headers and footers."""
        # Replace form feeds
        text = raw_text.replace("\x0c", "\n\n").replace("\f", "\n\n")

        # Strip standard RFC page footer/header patterns like "[Page 12]" or "RFC 8200   IPv6 Specification"
        lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            # Skip page footer line
            if re.search(r"\[Page\s+\d+\]$", stripped, re.IGNORECASE):
                continue
            # Skip header line like "RFC 8200 ... July 2017"
            if re.search(r"^RFC\s+\d+.*?(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}", stripped, re.IGNORECASE):
                continue
            lines.append(line)

        return "\n".join(lines)

    def _split_into_sections(self, cleaned_text: str) -> List[Dict[str, str]]:
        """Identify RFC section headers and divide text into sections."""
        lines = cleaned_text.split("\n")
        sections: List[Dict[str, str]] = []

        current_sec_num = "0"
        current_sec_title = "Preamble"
        current_lines: List[str] = []

        # Regex for section headers, e.g. "1. Introduction", "3.2. Address Format", "Appendix A."
        sec_header_pattern = re.compile(
            r"^([0-9]+(?:\.[0-9]+)*\.?|[A-Z]\.|\bAbstract\b|\bStatus of This Memo\b|\bCopyright Notice\b|\bTable of Contents\b|\bSecurity Considerations\b|\bIANA Considerations\b|\bReferences\b|\bAuthors' Addresses\b)\s*(.*)$",
            re.IGNORECASE,
        )

        for line in lines:
            stripped = line.strip()
            # A potential section heading is usually not indented much and relatively short
            if stripped and len(stripped) < 80 and not line.startswith("   "):
                m = sec_header_pattern.match(stripped)
                if m:
                    # Save previous section
                    sec_text = "\n".join(current_lines).strip()
                    if sec_text:
                        sections.append(
                            {
                                "section_number": current_sec_num,
                                "section_title": current_sec_title,
                                "text": sec_text,
                            }
                        )
                    # New section header
                    prefix = m.group(1).rstrip(".")
                    title = m.group(2).strip() or prefix
                    current_sec_num = prefix
                    current_sec_title = title
                    current_lines = []
                    continue

            current_lines.append(line)

        # Append last section
        sec_text = "\n".join(current_lines).strip()
        if sec_text:
            sections.append(
                {
                    "section_number": current_sec_num,
                    "section_title": current_sec_title,
                    "text": sec_text,
                }
            )

        return sections

    def _subchunk_text(self, text: str) -> List[str]:
        """Sub-chunk long section texts by paragraphs with overlap."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[str] = []
        curr_chunk: List[str] = []
        curr_len = 0

        for para in paragraphs:
            para_len = len(para)
            if curr_len + para_len + 2 > self.max_chunk_chars and curr_chunk:
                combined = "\n\n".join(curr_chunk)
                chunks.append(combined)
                # Keep last paragraph for overlap if reasonable
                if len(curr_chunk[-1]) <= self.chunk_overlap_chars:
                    curr_chunk = [curr_chunk[-1], para]
                    curr_len = len(curr_chunk[0]) + para_len + 2
                else:
                    curr_chunk = [para]
                    curr_len = para_len
            else:
                curr_chunk.append(para)
                curr_len += para_len + 2

        if curr_chunk:
            chunks.append("\n\n".join(curr_chunk))

        return chunks if chunks else [text]

    def chunk_file(self, file_path: Path) -> List[DocumentChunk]:
        """Process a single RFC text file into DocumentChunks."""
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
        rfc_id = file_path.stem.lower()
        rfc_num = rfc_id.replace("rfc", "")

        meta = self.metadata_map.get(rfc_id, {})
        rfc_title = meta.get("title", f"RFC {rfc_num}")
        wg = meta.get("wg", "Unknown")

        cleaned = self._clean_rfc_text(raw_text)
        sections = self._split_into_sections(cleaned)

        doc_chunks: List[DocumentChunk] = []
        chunk_counter = 0

        for sec in sections:
            sec_num = sec["section_number"]
            sec_title = sec["section_title"]
            # Skip empty or pure TOC sections
            if "Table of Contents" in sec_title and len(sec["text"]) > 3000:
                continue

            sub_chunks = self._subchunk_text(sec["text"])
            for sub_text in sub_chunks:
                if not sub_text.strip():
                    continue

                chunk_id = f"{rfc_id}_s{sec_num}_{chunk_counter}"
                # Construct clean textual representation embedding section header
                formatted_text = f"RFC {rfc_num} ({rfc_title})\nSection {sec_num}: {sec_title}\n\n{sub_text}"

                doc_chunks.append(
                    DocumentChunk(
                        id=chunk_id,
                        rfc_id=rfc_id,
                        rfc_number=rfc_num,
                        rfc_title=rfc_title,
                        wg=wg,
                        section_number=sec_num,
                        section_title=sec_title,
                        text=formatted_text,
                        chunk_index=chunk_counter,
                    )
                )
                chunk_counter += 1

        return doc_chunks
