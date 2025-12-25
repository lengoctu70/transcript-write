"""Streamlit app for transcript cleaning"""
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
import os

from src import (
    TranscriptParser,
    SmartChunker,
    LLMProcessor,
    OutputValidator,
    MarkdownWriter,
    CostEstimator,
    process_transcript
)

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="Transcript Cleaner",
    page_icon="📝",
    layout="wide"
)


def main():
    st.title("📝 Transcript Cleaning Tool")
    st.markdown("Convert lecture transcripts to clean study notes")

    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")

        # API Key
        api_key = st.text_input(
            "Anthropic API Key",
            value=os.getenv("ANTHROPIC_API_KEY", ""),
            type="password",
            help="Get your API key from console.anthropic.com"
        )

        # Model selection
        model = st.selectbox(
            "Model",
            options=[
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022"
            ],
            help="Sonnet: Higher quality, higher cost. Haiku: Faster, cheaper."
        )

        # Chunking config
        st.subheader("Chunking")
        chunk_size = st.slider(
            "Chunk size (chars)",
            min_value=1000,
            max_value=4000,
            value=2000,
            step=500,
            help="Smaller = more API calls but better context handling"
        )

        overlap = st.slider(
            "Context overlap (chars)",
            min_value=0,
            max_value=500,
            value=200,
            step=50,
            help="Context from previous chunk included for continuity"
        )

        st.divider()
        st.caption("Built with Streamlit + Claude API")

    # Main content area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Upload Transcript")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["srt", "vtt"],
            help="Supported formats: SRT, VTT"
        )

        video_title = st.text_input(
            "Video Title",
            value="",
            placeholder="e.g., Machine Learning Lecture 1"
        )

    # Process if file uploaded
    if uploaded_file is not None:
        # Parse transcript
        parser = TranscriptParser()
        try:
            segments = parser.parse_from_bytes(
                uploaded_file.getvalue(),
                uploaded_file.name
            )
            plain_text = parser.to_plain_text(segments)
        except Exception as e:
            st.error(f"Error parsing file: {e}")
            return

        # Use filename as default title
        if not video_title:
            video_title = Path(uploaded_file.name).stem

        # Show original preview
        with col1:
            with st.expander("Preview original transcript", expanded=False):
                st.text(plain_text[:2000] + ("..." if len(plain_text) > 2000 else ""))
                st.caption(f"Total length: {len(plain_text):,} characters")

        # Chunk transcript
        chunker = SmartChunker(chunk_size=chunk_size, overlap=overlap)
        chunks = chunker.chunk_transcript(plain_text)

        with col2:
            st.subheader("2. Cost Estimate")

            # Estimate cost
            estimator = CostEstimator(model=model)
            prompt_path = Path(__file__).parent / "prompts" / "base_prompt.txt"

            if prompt_path.exists():
                prompt_template = prompt_path.read_text()
                estimate = estimator.estimate_total(chunks, prompt_template)

                # Display estimate
                metric_cols = st.columns(3)
                with metric_cols[0]:
                    st.metric("Estimated Cost", f"${estimate.total_cost:.4f}")
                with metric_cols[1]:
                    st.metric("Chunks", estimate.chunks)
                with metric_cols[2]:
                    st.metric("Est. Time", f"~{estimate.processing_time_minutes} min")

                with st.expander("Cost breakdown"):
                    st.markdown(estimator.format_estimate(estimate))
            else:
                st.warning("Prompt template not found. Create prompts/base_prompt.txt")
                estimate = None

        # Process button
        if api_key and estimate:
            st.divider()

            # Confirmation for high costs
            if estimate.total_cost > 1.0:
                st.warning(f"⚠️ Estimated cost is ${estimate.total_cost:.2f}. Please confirm.")
                confirm = st.checkbox("I understand and want to proceed")
                if not confirm:
                    return

            if st.button("🚀 Process Transcript", type="primary", use_container_width=True):
                process_transcript_ui(
                    chunks=chunks,
                    api_key=api_key,
                    model=model,
                    video_title=video_title,
                    prompt_template=prompt_template
                )

        elif not api_key:
            st.info("👈 Enter your API key in the sidebar to continue")


def process_transcript_ui(
    chunks: list,
    api_key: str,
    model: str,
    video_title: str,
    prompt_template: str
):
    """Process transcript with progress tracking"""

    # Progress UI
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current: int, total: int):
        progress_bar.progress(current / total)
        status_text.text(f"Processing chunk {current}/{total}...")

    # Process
    try:
        results, summary = process_transcript(
            chunks=chunks,
            api_key=api_key,
            video_title=video_title,
            model=model,
            progress_callback=update_progress
        )
    except Exception as e:
        st.error(f"Processing failed: {e}")
        return

    # Clear progress
    progress_bar.empty()
    status_text.empty()

    # Validate output
    validator = OutputValidator()
    validation = validator.validate_all(results)

    if validation.has_errors or validation.has_warnings:
        with st.expander(
            f"⚠️ Validation: {validation.error_count} errors, {validation.warning_count} warnings",
            expanded=validation.has_errors
        ):
            for issue in validation.issues:
                icon = "❌" if issue.severity.value == "error" else "⚠️"
                st.markdown(f"{icon} **{issue.rule}**: {issue.message}")
                if issue.snippet:
                    st.code(issue.snippet, language=None)

    # Write output
    writer = MarkdownWriter()
    md_path, json_path = writer.write(
        processed_chunks=results,
        title=video_title,
        summary=summary
    )

    # Success message
    st.success(f"✅ Processing complete! Cost: ${summary['total_cost']:.4f}")

    # Show results
    st.subheader("3. Results")

    # Tabs for preview and download
    tab1, tab2, tab3 = st.tabs(["Preview", "Full Output", "Stats"])

    with tab1:
        preview = writer.get_content_for_preview(results, max_chars=3000)
        st.markdown(preview)

    with tab2:
        full_content = md_path.read_text()
        st.markdown(full_content)

    with tab3:
        st.json(summary)

    # Download buttons
    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="📥 Download Markdown",
            data=md_path.read_bytes(),
            file_name=md_path.name,
            mime="text/markdown",
            use_container_width=True
        )

    with col2:
        st.download_button(
            label="📥 Download Metadata (JSON)",
            data=json_path.read_bytes(),
            file_name=json_path.name,
            mime="application/json",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
