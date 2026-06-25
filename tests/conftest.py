"""Shared fixtures for ViLAW tests."""

import os
import sys
import tempfile

import pytest

# Ensure project root is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(autouse=True)
def set_env():
    """Set minimal env vars so settings can be imported without .env file."""
    os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
    os.environ.setdefault("INDEX_DIR", tempfile.mkdtemp())
    os.environ.setdefault("BOPD_ZIP_URL", "https://example.com/test.zip")
    os.environ.setdefault("EMBEDDER_BACKEND", "builtin")
    yield


@pytest.fixture
def sample_document():
    return {
        "id": "chu_de=Test|de_muc=Test|dieu=Điều 1",
        "chu_de": "Test",
        "de_muc": "Test",
        "so_dieu": "Điều 1",
        "tieu_de_dieu": "Phạm vi điều chỉnh",
        "noi_dung": (
            "Điều 1. Phạm vi điều chỉnh\n"
            "Luật này quy định về tổ chức và hoạt động của Chính phủ.\n"
            "Điều 2. Giải thích từ ngữ\n"
            "Trong Luật này, các từ ngữ dưới đây được hiểu như sau:\n"
            "1. Chính phủ là cơ quan hành chính nhà nước cao nhất.\n"
            "2. Thủ tướng là người đứng đầu Chính phủ.\n"
            "Điều 3. Áp dụng Luật\nLuật này áp dụng đối với các cơ quan nhà nước."
        ),
        "nguon": "Test source",
        "path_goc": "/tmp/test.html",
    }


@pytest.fixture
def sample_legal_query():
    return "Điều 1 quy định về phạm vi điều chỉnh như thế nào?"


@pytest.fixture
def sample_general_query():
    return "Chính phủ có quyền hạn gì?"
