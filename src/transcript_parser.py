"""Parse subtitle files to structured format"""
from dataclasses import dataclass
from typing import List, Union
from pathlib import Path
import pysrt
import webvtt
import re


@dataclass
class TranscriptSegment:
    """Single subtitle segment"""
    index: int
    start_time: str  # HH:MM:SS format
    end_time: str
    text: str


class TranscriptParser:
    """Parse SRT/VTT files to text with timestamps"""

    def parse(self, file_path: Union[str, Path]) -> List[TranscriptSegment]:
        """Auto-detect format and parse"""
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".srt":
            return self._parse_srt(path)
        elif suffix == ".vtt":
            return self._parse_vtt(path)
        else:
            raise ValueError(f"Unsupported format: {suffix}")

    def parse_from_bytes(
        self, content: bytes, filename: str
    ) -> List[TranscriptSegment]:
        """Parse from uploaded file bytes (Streamlit)"""
        import tempfile
        import os

        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=suffix, delete=False
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            return self.parse(temp_path)
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def _parse_srt(self, path: Path) -> List[TranscriptSegment]:
        """Parse SRT file"""
        subs = pysrt.open(str(path))
        segments = []

        for sub in subs:
            segments.append(TranscriptSegment(
                index=sub.index,
                start_time=self._format_time(sub.start),
                end_time=self._format_time(sub.end),
                text=self._clean_text(sub.text)
            ))

        return self._deduplicate(segments)

    def _parse_vtt(self, path: Path) -> List[TranscriptSegment]:
        """Parse VTT file"""
        vtt = webvtt.read(str(path))
        segments = []

        for i, caption in enumerate(vtt):
            segments.append(TranscriptSegment(
                index=i + 1,
                start_time=self._vtt_time_to_str(caption.start),
                end_time=self._vtt_time_to_str(caption.end),
                text=self._clean_text(caption.text)
            ))

        return self._deduplicate(segments)

    def _format_time(self, time_obj) -> str:
        """Format pysrt time to HH:MM:SS"""
        return f"{time_obj.hours:02d}:{time_obj.minutes:02d}:{time_obj.seconds:02d}"

    def _vtt_time_to_str(self, time_str: str) -> str:
        """Convert VTT time (00:00:00.000) to HH:MM:SS"""
        parts = time_str.split(":")
        if len(parts) == 2:
            return f"00:{parts[0]}:{parts[1].split('.')[0]}"
        else:
            return f"{parts[0]}:{parts[1]}:{parts[2].split('.')[0]}"

    def _clean_text(self, text: str) -> str:
        """Remove HTML tags and normalize whitespace"""
        text = re.sub(r"<[^>]+>", "", text)
        text = " ".join(text.split())
        return text.strip()

    def _normalize_transcript_whitespace(self, text: str) -> str:
        """Aggressive whitespace normalization for lecture transcripts.

        Designed for educational content only - no code blocks, tables, poetry.
        Reduces false paragraph boundaries from SRT format.

        Args:
            text: Raw transcript text with timestamps

        Returns:
            Normalized text with reduced whitespace
        """
        # Collapse all multiple newlines to max 2 (paragraph break)
        text = re.sub(r'\n{2,}', '\n\n', text)

        # Remove whitespace around timestamps: \n[00:00:00]\n -> \n[00:00:00]
        text = re.sub(r'\n+(\[[\d:]+\])\n+', r'\n\1 ', text)

        # Strip line-level whitespace
        text = '\n'.join(line.strip() for line in text.split('\n'))

        # Remove remaining multiple empty lines
        text = re.sub(r'\n\n+', '\n\n', text)

        return text.strip()

    def _deduplicate(
        self, segments: List[TranscriptSegment]
    ) -> List[TranscriptSegment]:
        """Remove consecutive duplicate texts (common in auto-captions)"""
        if not segments:
            return segments

        result = [segments[0]]
        for seg in segments[1:]:
            if seg.text != result[-1].text:
                result.append(seg)

        return result

    def to_plain_text(self, segments: List[TranscriptSegment]) -> str:
        """Convert segments to timestamped plain text with normalization"""
        lines = []
        current_time = None

        for seg in segments:
            if current_time != seg.start_time:
                lines.append(f"\n[{seg.start_time}]")
                current_time = seg.start_time

            lines.append(seg.text)

        raw_text = "\n".join(lines)
        return self._normalize_transcript_whitespace(raw_text)
