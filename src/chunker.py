"""Smart chunking with context preservation"""
from dataclasses import dataclass
from typing import List, Optional
import re


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    index: int
    text: str
    start_timestamp: str
    context_buffer: Optional[str] = None

    @property
    def full_text_for_llm(self) -> str:
        """Build text to send to LLM"""
        parts = []
        if self.context_buffer:
            parts.append("[CONTEXT FROM PREVIOUS SECTION]")
            parts.append(self.context_buffer)
            parts.append("")

        parts.append("[NEW CONTENT TO PROCESS]")
        parts.append(self.text)

        return "\n".join(parts)

    @property
    def char_count(self) -> int:
        """Total chars including context"""
        return len(self.full_text_for_llm)


class SmartChunker:
    """Split transcript at sentence boundaries with context"""

    def __init__(self, chunk_size: int = 2000, overlap: int = 200):
        """
        Args:
            chunk_size: Target characters per chunk (excluding context)
            overlap: Characters to include from previous chunk as context
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_transcript(self, text: str) -> List[Chunk]:
        """Split transcript into chunks with context preservation"""
        chunks = []
        current_pos = 0
        chunk_index = 0
        previous_chunk_text = ""

        while current_pos < len(text):
            end_pos = min(current_pos + self.chunk_size, len(text))

            if end_pos < len(text):
                end_pos = self._find_best_split(text, current_pos, end_pos)

            chunk_text = text[current_pos:end_pos].strip()

            if not chunk_text:
                current_pos = end_pos
                continue

            context_buffer = None
            if previous_chunk_text and chunk_index > 0:
                context_buffer = self._get_context_buffer(previous_chunk_text)

            start_ts = self._extract_first_timestamp(chunk_text)

            chunks.append(Chunk(
                index=chunk_index,
                text=chunk_text,
                start_timestamp=start_ts or "00:00:00",
                context_buffer=context_buffer
            ))

            previous_chunk_text = chunk_text
            current_pos = end_pos
            chunk_index += 1

        return chunks

    def _find_best_split(
        self, text: str, start: int, target_end: int
    ) -> int:
        """Find best split point near target_end (prefer sentence boundary)"""
        search_start = max(start, target_end - 100)
        search_text = text[search_start:target_end + 50]

        para_match = list(re.finditer(r"\n\n", search_text))
        if para_match:
            return search_start + para_match[-1].end()

        sent_match = list(re.finditer(r"[.!?][\s\n]", search_text))
        if sent_match:
            return search_start + sent_match[-1].end()

        ts_match = list(re.finditer(r"\[[\d:]+\]", search_text))
        if ts_match:
            return search_start + ts_match[-1].start()

        return target_end

    def _get_context_buffer(self, previous_text: str) -> str:
        """Extract last N chars from previous chunk as context"""
        if len(previous_text) <= self.overlap:
            return previous_text

        text = previous_text[-self.overlap - 50:]
        sent_match = re.search(r"[.!?]\s+", text)

        if sent_match:
            return text[sent_match.end():].strip()

        return previous_text[-self.overlap:].strip()

    def _extract_first_timestamp(self, text: str) -> Optional[str]:
        """Extract first timestamp [HH:MM:SS] from text"""
        match = re.search(r"\[(\d{2}:\d{2}:\d{2})\]", text)
        return match.group(1) if match else None
