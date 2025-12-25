"""Format and save cleaned transcript as Markdown"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from pathlib import Path
import json
import re


@dataclass
class TranscriptMetadata:
    """Metadata for processed transcript"""
    title: str
    original_duration: Optional[str]
    processed_at: str
    model: str
    total_cost: float
    chunks_processed: int
    input_tokens: int
    output_tokens: int


class MarkdownWriter:
    """Write cleaned transcript to Markdown file"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def write(
        self,
        processed_chunks: list,
        title: str,
        summary: dict,
        duration: Optional[str] = None
    ) -> tuple[Path, Path]:
        """
        Write cleaned transcript to Markdown and metadata to JSON.

        Returns:
            (markdown_path, metadata_path)
        """
        metadata = TranscriptMetadata(
            title=title,
            original_duration=duration,
            processed_at=datetime.now().isoformat(),
            model=summary["model"],
            total_cost=summary["total_cost"],
            chunks_processed=summary["chunks_processed"],
            input_tokens=summary["total_input_tokens"],
            output_tokens=summary["total_output_tokens"]
        )

        content = self._build_markdown(processed_chunks, metadata)

        safe_title = self._sanitize_filename(title)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base_name = f"{safe_title}-{timestamp}"

        md_path = self.output_dir / f"{base_name}.md"
        json_path = self.output_dir / f"{base_name}-metadata.json"

        md_path.write_text(content, encoding="utf-8")
        json_path.write_text(
            json.dumps(self._metadata_to_dict(metadata), indent=2),
            encoding="utf-8"
        )

        return md_path, json_path

    def _build_markdown(
        self,
        chunks: list,
        metadata: TranscriptMetadata
    ) -> str:
        """Build complete Markdown document"""
        lines = []

        lines.append(f"# {metadata.title}")
        lines.append("")

        lines.append(f"**Processed:** {metadata.processed_at[:10]}")
        lines.append(f"**Model:** {metadata.model}")
        lines.append(f"**Cost:** ${metadata.total_cost:.4f}")
        if metadata.original_duration:
            lines.append(f"**Duration:** {metadata.original_duration}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for chunk in chunks:
            cleaned = chunk.cleaned_text.strip()
            if cleaned:
                lines.append(cleaned)
                lines.append("")

        return "\n".join(lines)

    def _metadata_to_dict(self, metadata: TranscriptMetadata) -> dict:
        """Convert metadata to dictionary"""
        return {
            "title": metadata.title,
            "original_duration": metadata.original_duration,
            "processed_at": metadata.processed_at,
            "model": metadata.model,
            "cost_usd": metadata.total_cost,
            "chunks_processed": metadata.chunks_processed,
            "tokens": {
                "input": metadata.input_tokens,
                "output": metadata.output_tokens,
                "total": metadata.input_tokens + metadata.output_tokens
            }
        }

    def _sanitize_filename(self, title: str) -> str:
        """Create safe filename from title"""
        safe = re.sub(r'[<>:"/\\|?*]', '', title)
        safe = re.sub(r'\s+', '-', safe)
        return safe[:50].strip('-')

    def get_content_for_preview(
        self, chunks: list, max_chars: int = 5000
    ) -> str:
        """Get preview content (for Streamlit display)"""
        content = []
        total_chars = 0

        for chunk in chunks:
            text = chunk.cleaned_text.strip()
            if total_chars + len(text) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 100:
                    content.append(text[:remaining] + "...")
                break
            content.append(text)
            total_chars += len(text)

        return "\n\n".join(content)
