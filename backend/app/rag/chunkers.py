"""Chunking strategies for document text."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod


class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, text: str, metadata: dict | None = None) -> list[dict]: ...


class FixedSizeChunker(BaseChunker):
    def __init__(self, chunk_size: int = 1200, overlap: int = 100) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: dict | None = None) -> list[dict]:
        meta = metadata or {}
        chunks = []
        i = 0
        idx = 0
        while i < len(text):
            end = min(i + self.chunk_size, len(text))
            chunk_text = text[i:end]
            chunks.append({
                "content": chunk_text,
                "metadata": {**meta, "chunk_index": idx, "start": i, "end": end},
            })
            idx += 1
            i += self.chunk_size - self.overlap
        return chunks


class ParagraphChunker(BaseChunker):
    def __init__(self, max_chunk_size: int = 2000, overlap: int = 100) -> None:
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: dict | None = None) -> list[dict]:
        meta = metadata or {}
        paragraphs = text.split("\n\n")
        chunks = []
        current = ""
        idx = 0
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) > self.max_chunk_size and current:
                chunks.append({"content": current.strip(), "metadata": {**meta, "chunk_index": idx}})
                idx += 1
                current = para if len(para) < self.max_chunk_size else para[-self.overlap:] + para
            else:
                current += "\n\n" + para if current else para
        if current.strip():
            chunks.append({"content": current.strip(), "metadata": {**meta, "chunk_index": idx}})
        return chunks


class HeadingChunker(BaseChunker):
    def __init__(self, max_chunk_size: int = 2000) -> None:
        self.max_chunk_size = max_chunk_size

    def chunk(self, text: str, metadata: dict | None = None) -> list[dict]:
        meta = metadata or {}
        sections = re.split(r"\n(?=#{1,6}\s)", text)
        chunks = []
        idx = 0
        for section in sections:
            section = section.strip()
            if not section:
                continue
            heading_match = re.match(r"^(#{1,6})\s+(.+)", section)
            heading = heading_match.group(2) if heading_match else ""
            if len(section) <= self.max_chunk_size:
                chunks.append({
                    "content": section,
                    "metadata": {**meta, "chunk_index": idx, "heading": heading},
                })
                idx += 1
            else:
                sub = FixedSizeChunker(self.max_chunk_size)
                sub_chunks = sub.chunk(section, {**meta, "heading": heading})
                for sc in sub_chunks:
                    sc["metadata"]["chunk_index"] = idx
                    chunks.append(sc)
                    idx += 1
        return chunks


class SemanticChunker(BaseChunker):
    """Sentence-boundary aware chunker — groups sentences up to max_chunk_size,
    preferring natural breaks at sentence endings."""

    def __init__(self, max_chunk_size: int = 1500, overlap_sentences: int = 1) -> None:
        self.max_chunk_size = max_chunk_size
        self.overlap_sentences = overlap_sentences

    def chunk(self, text: str, metadata: dict | None = None) -> list[dict]:
        meta = metadata or {}
        sentences = self._split_sentences(text)
        if not sentences:
            return []
        chunks = []
        idx = 0
        i = 0
        while i < len(sentences):
            current = sentences[i]
            j = i + 1
            while j < len(sentences) and len(current) + len(sentences[j]) < self.max_chunk_size:
                current += " " + sentences[j] if current else sentences[j]
                j += 1
            chunks.append({"content": current.strip(), "metadata": {**meta, "chunk_index": idx}})
            idx += 1
            if j >= len(sentences):
                break
            i = max(j - self.overlap_sentences, i + 1)
        return chunks

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        return [s.strip() for s in re.split(r"(?<=[。！？.!?])\s*", text) if s.strip()]
