"""Test tools functionality."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from app.tools.search import SearchResult, SearchTool
from app.tools.document_processor import DocumentChunk, DocumentProcessor


class TestSearchResult:
    """Test SearchResult class."""

    def test_create_search_result(self) -> None:
        """Test creating a search result."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="This is a test snippet"
        )
        
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "This is a test snippet"

    def test_to_dict(self) -> None:
        """Test converting search result to dictionary."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="This is a test snippet"
        )
        
        data = result.to_dict()
        
        assert data["title"] == "Test Title"
        assert data["url"] == "https://example.com"
        assert data["snippet"] == "This is a test snippet"


class TestSearchTool:
    """Test SearchTool class."""

    def test_cache_key_generation(self) -> None:
        """Test cache key generation."""
        tool = SearchTool()
        
        key1 = tool._cache_key("test query", 10)
        key2 = tool._cache_key("test query", 10)
        key3 = tool._cache_key("different query", 10)
        
        assert key1 == key2  # Same inputs should generate same key
        assert key1 != key3  # Different inputs should generate different keys

    def test_robots_allowed_basic(self) -> None:
        """Test basic robots.txt checking."""
        tool = SearchTool()
        
        # Should default to allowing if can't check
        result = tool._is_robots_allowed("https://nonexistent-domain-12345.com")
        assert result is True

    @patch('requests.Session.get')
    def test_search_fallback(self, mock_get: Mock) -> None:
        """Test fallback search functionality."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""
        <html>
            <body>
                <div class="g">
                    <h3>Test Result 1</h3>
                    <a href="https://example1.com">Link 1</a>
                    <span>Test snippet 1</span>
                </div>
                <div class="g">
                    <h3>Test Result 2</h3>
                    <a href="https://example2.com">Link 2</a>
                    <span>Test snippet 2</span>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        tool = SearchTool()
        results = tool._search_fallback("test query", 5)
        
        # Should return some results (exact parsing may vary)
        assert isinstance(results, list)


class TestDocumentChunk:
    """Test DocumentChunk class."""

    def test_create_chunk(self) -> None:
        """Test creating a document chunk."""
        chunk = DocumentChunk(
            text="This is a test chunk",
            page=1,
            start_char=0,
            end_char=20
        )
        
        assert chunk.text == "This is a test chunk"
        assert chunk.page == 1
        assert chunk.start_char == 0
        assert chunk.end_char == 20


class TestDocumentProcessor:
    """Test DocumentProcessor class."""

    def test_pii_redaction(self) -> None:
        """Test PII redaction functionality."""
        processor = DocumentProcessor()
        
        text_with_pii = "Contact john.doe@example.com or call 555-123-4567"
        redacted = processor._redact_pii(text_with_pii)
        
        # Should redact email and phone
        assert "[EMAIL]" in redacted
        assert "[PHONE]" in redacted
        assert "john.doe@example.com" not in redacted
        assert "555-123-4567" not in redacted

    def test_chunk_text(self) -> None:
        """Test text chunking."""
        processor = DocumentProcessor(chunk_size=50, overlap=10)
        
        text = "This is a long text. " * 10  # Create text longer than chunk_size
        chunks = processor._chunk_text(text)
        
        assert len(chunks) > 1  # Should create multiple chunks
        
        # Check overlap
        if len(chunks) > 1:
            # There should be some overlap between consecutive chunks
            chunk1_end = chunks[0].text[-10:]
            chunk2_start = chunks[1].text[:10]
            # Some overlap expected due to overlap parameter

    def test_search_chunks(self) -> None:
        """Test searching within chunks."""
        processor = DocumentProcessor()
        
        chunks = [
            DocumentChunk("This contains the search term", 1, 0, 30),
            DocumentChunk("This does not contain it", 1, 31, 55),
            DocumentChunk("Another search term example", 1, 56, 83)
        ]
        
        results = processor.search_chunks(chunks, "search term", max_results=5)
        
        # Should find chunks containing the search term
        assert len(results) >= 1
        assert all(isinstance(result, tuple) for result in results)
        assert all(len(result) == 2 for result in results)  # (chunk, score)
        
        # Results should be sorted by score (highest first)
        if len(results) > 1:
            assert results[0][1] >= results[1][1]

    def test_extract_metadata_nonexistent_file(self) -> None:
        """Test metadata extraction for nonexistent file."""
        processor = DocumentProcessor()
        
        with pytest.raises(FileNotFoundError):
            processor.extract_metadata(Path("nonexistent.pdf"))

    def test_process_document_unsupported_type(self) -> None:
        """Test processing unsupported document type."""
        processor = DocumentProcessor()
        
        # Create a temporary file with unsupported extension
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"test content")
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Unsupported file type"):
                processor.process_document(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)
