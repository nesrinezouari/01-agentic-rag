"""
gitsource: GitHub repository reader with document chunking for RAG/LLM applications.
"""

from gitsource.__version__ import __version__
from gitsource.chunking import chunk_documents, sliding_window
from gitsource.github import (
    GithubRepositoryDataReader,
    notebook_processor,
    Processor,
    RawRepositoryFile,
)
from gitsource.notebook import (
    CellInfo,
    extract_cells,
    load_notebook,
    loads_notebook,
    loads_notebook_to_markdown,
    NotebookDict,
    notebook_to_markdown,
    notebook_to_text,
)

__all__ = [
    "__version__",
    # GitHub repository fetching
    "GithubRepositoryDataReader",
    "RawRepositoryFile",
    "Processor",
    "notebook_processor",
    # Document chunking
    "chunk_documents",
    "sliding_window",
    # Notebook parsing
    "load_notebook",
    "loads_notebook",
    "NotebookDict",
    "CellInfo",
    "extract_cells",
    "notebook_to_text",
    "notebook_to_markdown",
    "loads_notebook_to_markdown",
]
