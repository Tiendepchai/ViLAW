import pytest
from shared.semantic_chunker import chunk_document, _parse_sections, _split_long_body


class TestParseSections:
    def test_detects_article_boundaries(self):
        text = "Mở đầu\nĐiều 1. Nội dung\nĐiều 2. Nội dung khác"
        sections = _parse_sections(text)
        assert len(sections) == 3
        assert sections[1]["header"] == "Điều 1."
        assert sections[2]["header"] == "Điều 2."

    def test_single_section(self):
        text = "Chỉ có một đoạn"
        sections = _parse_sections(text)
        assert len(sections) == 1


class TestSplitLongBody:
    def test_short_body_not_split(self):
        text = "Đoạn ngắn."
        parts = _split_long_body(text, max_len=1000)
        assert len(parts) == 1

    def test_long_body_split(self):
        text = "\n".join([f"Đoạn dài số {i} " * 20 for i in range(20)])
        parts = _split_long_body(text, max_len=200)
        assert len(parts) > 1

    def test_overlap_lines(self):
        text = "\n".join([f"Paragraph {i}" for i in range(10)])
        parts = _split_long_body(text, max_len=30, overlap_lines=2)
        assert len(parts) >= 2


class TestChunkDocument:
    def test_chunks_have_ids_and_text(self, sample_document):
        results = chunk_document(sample_document["id"], sample_document["noi_dung"])
        assert len(results) >= 1
        for c in results:
            assert "id" in c
            assert "text" in c
            assert "meta" in c
            assert c["meta"]["doc_id"] == sample_document["id"]

    def test_meta_passthrough(self, sample_document):
        meta = {"chu_de": "Test Pass"}
        results = chunk_document(sample_document["id"], sample_document["noi_dung"], meta=meta)
        assert results[0]["meta"]["chu_de"] == "Test Pass"

    def test_empty_text(self):
        results = chunk_document("doc1", "")
        assert results == []

    def test_section_in_chunks(self, sample_document):
        results = chunk_document(sample_document["id"], sample_document["noi_dung"])
        # First chunk should reference Điều 1
        assert any("Điều 1" in c["text"] for c in results)
