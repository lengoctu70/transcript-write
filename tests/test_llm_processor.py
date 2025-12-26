"""Tests for LLM processor with mocked API calls"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.chunker import Chunk
from src.llm_processor import (
    LLMProcessor,
    LLMProvider,
    ProcessedChunk,
    ProcessingError,
    process_transcript
)


class TestProcessedChunk:
    """Test ProcessedChunk dataclass"""

    def test_processed_chunk_creation(self):
        """Create ProcessedChunk with all fields"""
        chunk = ProcessedChunk(
            chunk_index=0,
            original_text="Original text",
            cleaned_text="Cleaned text",
            input_tokens=100,
            output_tokens=80,
            cost=0.0015,
            model="claude-3-5-sonnet-20241022",
            provider="anthropic"
        )
        assert chunk.chunk_index == 0
        assert chunk.original_text == "Original text"
        assert chunk.cleaned_text == "Cleaned text"
        assert chunk.input_tokens == 100
        assert chunk.output_tokens == 80
        assert chunk.cost == 0.0015
        assert chunk.provider == "anthropic"


class TestProcessingError:
    """Test ProcessingError exception"""

    def test_processing_error_creation(self):
        """Create ProcessingError with recoverable flag"""
        error = ProcessingError(
            chunk_index=1,
            message="API timeout",
            recoverable=True
        )
        assert error.chunk_index == 1
        assert error.message == "API timeout"
        assert error.recoverable is True
        assert "Chunk 1: API timeout" in str(error)


class TestLLMProcessor:
    """Test LLMProcessor class"""

    def test_init_with_api_key(self):
        """Initialize with explicit API key"""
        with patch('src.llm_processor.anthropic.Anthropic'):
            processor = LLMProcessor(api_key="test-key-123")
            assert processor.api_key == "test-key-123"
            assert processor.model == "claude-3-5-sonnet-20241022"

    def test_init_without_api_key_raises_error(self):
        """Raise ValueError when no API key provided"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="API key required"):
                LLMProcessor(api_key=None)

    def test_init_from_env_var(self):
        """Initialize API key from environment variable"""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'env-key-456'}):
            with patch('src.llm_processor.anthropic.Anthropic'):
                processor = LLMProcessor()
                assert processor.api_key == "env-key-456"

    def test_load_prompt_template_default_path(self):
        """Load prompt template from default path"""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "Template content"
            with patch('src.llm_processor.anthropic.Anthropic'):
                processor = LLMProcessor(api_key="test-key")
                template = processor.load_prompt_template()
                assert template == "Template content"

    def test_load_prompt_template_missing_file(self):
        """Raise FileNotFoundError when template file missing"""
        with patch('src.llm_processor.anthropic.Anthropic'):
            processor = LLMProcessor(api_key="test-key")
            with pytest.raises(FileNotFoundError, match="Prompt template not found"):
                processor.load_prompt_template("/nonexistent/path.txt")

    def test_cost_calculation_sonnet(self):
        """Calculate cost for Sonnet model"""
        with patch('src.llm_processor.anthropic.Anthropic'):
            processor = LLMProcessor(api_key="test-key", model="claude-3-5-sonnet-20241022")
            cost = processor._calculate_cost(input_tokens=1000, output_tokens=500)
            # Sonnet: $0.003/1K input, $0.015/1K output
            # (1000/1000 * 0.003) + (500/1000 * 0.015) = 0.003 + 0.0075 = 0.0105
            assert cost == 0.0105

    def test_cost_calculation_haiku(self):
        """Calculate cost for Haiku model"""
        with patch('src.llm_processor.anthropic.Anthropic'):
            processor = LLMProcessor(api_key="test-key", model="claude-3-5-haiku-20241022")
            cost = processor._calculate_cost(input_tokens=1000, output_tokens=500)
            # Haiku: $0.001/1K input, $0.005/1K output
            # (1000/1000 * 0.001) + (500/1000 * 0.005) = 0.001 + 0.0025 = 0.0035
            assert cost == 0.0035

    def test_build_prompt(self):
        """Build prompt with chunk and template"""
        chunk = Chunk(
            index=0,
            text="New content",
            start_timestamp="00:01:00",
            context_buffer="Previous content"
        )
        template = "Video: {{fileName}}\nContent: {{chunkText}}"

        with patch('src.llm_processor.anthropic.Anthropic'):
            processor = LLMProcessor(api_key="test-key")
            prompt = processor._build_prompt(chunk, template, "Test Video")

            assert "Video: Test Video" in prompt
            assert "[CONTEXT FROM PREVIOUS SECTION]" in prompt
            assert "Previous content" in prompt
            assert "[NEW CONTENT TO PROCESS]" in prompt
            assert "New content" in prompt

    @patch('src.llm_processor.anthropic.Anthropic')
    def test_process_chunk_success(self, mock_anthropic):
        """Successfully process a chunk"""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="Cleaned output text")]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 80

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        # Create chunk and process
        chunk = Chunk(index=0, text="Original text", start_timestamp="00:00:00")
        template = "Clean: {{chunkText}}"

        processor = LLMProcessor(api_key="test-key")
        result = processor.process_chunk(chunk, template, "Test Video")

        assert result.chunk_index == 0
        assert result.original_text == "Original text"
        assert result.cleaned_text == "Cleaned output text"
        assert result.input_tokens == 100
        assert result.output_tokens == 80
        assert result.model == "claude-3-5-sonnet-20241022"
        assert result.provider == "anthropic"

    @patch('src.llm_processor.anthropic.Anthropic')
    def test_process_all_chunks_with_callback(self, mock_anthropic):
        """Process multiple chunks with progress callback"""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="Cleaned")]
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 40

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        chunks = [
            Chunk(index=0, text="Text 0", start_timestamp="00:00:00"),
            Chunk(index=1, text="Text 1", start_timestamp="00:01:00"),
            Chunk(index=2, text="Text 2", start_timestamp="00:02:00"),
        ]
        template = "Clean: {{chunkText}}"

        # Track callback calls
        callback_calls = []
        def track_progress(current, total):
            callback_calls.append((current, total))

        processor = LLMProcessor(api_key="test-key")
        results = processor.process_all_chunks(chunks, template, progress_callback=track_progress)

        assert len(results) == 3
        assert callback_calls == [(1, 3), (2, 3), (3, 3)]

    @patch('src.llm_processor.anthropic.Anthropic')
    def test_process_all_chunks_without_callback(self, mock_anthropic):
        """Process chunks without progress callback"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Cleaned")]
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 40

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        chunks = [
            Chunk(index=0, text="Text", start_timestamp="00:00:00"),
        ]
        template = "Clean: {{chunkText}}"

        processor = LLMProcessor(api_key="test-key")
        results = processor.process_all_chunks(chunks, template)

        assert len(results) == 1


class TestProcessTranscript:
    """Test convenience function"""

    @patch('src.llm_processor.anthropic.Anthropic')
    def test_process_transcript_returns_summary(self, mock_anthropic):
        """Process transcript and return summary with totals"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Cleaned")]
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 80

        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        chunks = [
            Chunk(index=0, text="Text 0", start_timestamp="00:00:00"),
            Chunk(index=1, text="Text 1", start_timestamp="00:01:00"),
        ]

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = "Template"
            results, summary = process_transcript(
                chunks=chunks,
                api_key="test-key",
                video_title="Test Video"
            )

        assert len(results) == 2
        assert summary["chunks_processed"] == 2
        assert summary["total_input_tokens"] == 200
        assert summary["total_output_tokens"] == 160
        assert summary["model"] == "claude-3-5-sonnet-20241022"
        assert "total_cost" in summary


class TestLLMProcessorDeepSeek:
    """Test LLMProcessor with DeepSeek provider"""

    @patch('builtins.__import__')
    def test_init_deepseek_provider(self, mock_import):
        """Initialize LLMProcessor with DeepSeek provider"""
        # Mock OpenAI import
        mock_openai = Mock()
        mock_openai.OpenAI = Mock()
        mock_import.return_value = mock_openai

        processor = LLMProcessor(
            api_key="test-deepseek-key",
            model="deepseek-chat",
            provider=LLMProvider.DEEPSEEK
        )
        assert processor.provider == LLMProvider.DEEPSEEK
        assert processor.model == "deepseek-chat"

    @patch('builtins.__import__')
    def test_init_deepseek_from_model(self, mock_import):
        """Provider inferred from DeepSeek model"""
        mock_openai = Mock()
        mock_openai.OpenAI = Mock()
        mock_import.return_value = mock_openai

        processor = LLMProcessor(
            api_key="test-key",
            model="deepseek-reasoner"
        )
        assert processor.provider == LLMProvider.DEEPSEEK

    def test_deepseek_missing_api_key(self):
        """Raise error when DeepSeek API key not provided"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
                LLMProcessor(model="deepseek-chat")

    @patch('builtins.__import__')
    def test_deepseek_api_key_from_env(self, mock_import):
        """Load DeepSeek API key from environment"""
        mock_openai = Mock()
        mock_openai.OpenAI = Mock()
        mock_import.return_value = mock_openai

        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'sk-deepseek-123'}):
            processor = LLMProcessor(model="deepseek-chat")
            assert processor.api_key == "sk-deepseek-123"

    @patch('builtins.__import__')
    def test_deepseek_process_chunk(self, mock_import):
        """Process chunk with DeepSeek API"""
        # Setup mock OpenAI module and client
        mock_openai = Mock()
        mock_client = Mock()

        # Setup mock response
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="DeepSeek cleaned text"))]
        mock_response.usage.prompt_tokens = 90
        mock_response.usage.completion_tokens = 70

        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client
        mock_import.return_value = mock_openai

        # Create chunk and process
        chunk = Chunk(index=0, text="Original text", start_timestamp="00:00:00")
        template = "Clean: {{chunkText}}"

        processor = LLMProcessor(
            api_key="test-key",
            model="deepseek-chat",
            provider=LLMProvider.DEEPSEEK
        )
        result = processor.process_chunk(chunk, template, "Test Video")

        assert result.chunk_index == 0
        assert result.cleaned_text == "DeepSeek cleaned text"
        assert result.input_tokens == 90
        assert result.output_tokens == 70
        assert result.model == "deepseek-chat"
        assert result.provider == "deepseek"

    @patch('builtins.__import__')
    def test_cost_calculation_deepseek_chat(self, mock_import):
        """Calculate cost for deepseek-chat model"""
        mock_openai = Mock()
        mock_openai.OpenAI = Mock()
        mock_import.return_value = mock_openai

        processor = LLMProcessor(
            api_key="test-key",
            model="deepseek-chat"
        )
        # deepseek-chat: $0.00027/1K input, $0.0011/1K output
        cost = processor._calculate_cost(1000, 500)
        assert round(cost, 6) == round((1000/1000) * 0.00027 + (500/1000) * 0.0011, 6)

    @patch('builtins.__import__')
    def test_cost_calculation_deepseek_reasoner(self, mock_import):
        """Calculate cost for deepseek-reasoner model"""
        mock_openai = Mock()
        mock_openai.OpenAI = Mock()
        mock_import.return_value = mock_openai

        processor = LLMProcessor(
            api_key="test-key",
            model="deepseek-reasoner"
        )
        # deepseek-reasoner: $0.00056/1K input, $0.0022/1K output
        cost = processor._calculate_cost(1000, 500)
        assert round(cost, 6) == round((1000/1000) * 0.00056 + (500/1000) * 0.0022, 6)


class TestLLMProviderEnum:
    """Test LLMProvider enum"""

    def test_provider_values(self):
        """Provider enum has correct values"""
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.DEEPSEEK.value == "deepseek"

    def test_model_provider_mapping(self):
        """Model to provider mapping is correct"""
        assert LLMProcessor.MODEL_PROVIDER["claude-3-5-sonnet-20241022"] == LLMProvider.ANTHROPIC
        assert LLMProcessor.MODEL_PROVIDER["claude-3-5-haiku-20241022"] == LLMProvider.ANTHROPIC
        assert LLMProcessor.MODEL_PROVIDER["deepseek-chat"] == LLMProvider.DEEPSEEK
        assert LLMProcessor.MODEL_PROVIDER["deepseek-reasoner"] == LLMProvider.DEEPSEEK

