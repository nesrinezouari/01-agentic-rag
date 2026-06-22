"""
GitHub repository data fetching module.

This module provides functionality to download and extract files from GitHub
repositories without requiring git to be installed.

Features:
- Processor registry for per-extension content transformation
- Built-in notebook processor for .ipynb files
"""

import io
import zipfile
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable

import frontmatter
import requests

from .notebook import loads_notebook, notebook_to_text


@dataclass
class RawRepositoryFile:
    """Dataclass representing a file from a GitHub repository.

    Attributes:
        filename: The path/filename of the file within the repository
        content: The text content of the file
    """
    filename: str
    content: str

    def parse(self) -> Dict[str, Any]:
        """Parse YAML frontmatter from the file content.

        Returns:
            Dictionary with frontmatter data plus filename and content

        Example:
            >>> file = RawRepositoryFile("doc.md", "---\\ntitle: Test\\n---\\ncontent")
            >>> parsed = file.parse()
            >>> parsed["title"]
            'Test'
            >>> parsed["filename"]
            'doc.md'
        """
        post = frontmatter.loads(self.content)
        data = post.to_dict()
        data["filename"] = self.filename
        return data


# Type alias for processor functions
Processor = Callable[[str, str], str]  # (content, filename) -> processed_content


def notebook_processor(content: str, filename: str) -> str:
    """Convert Jupyter notebook JSON to markdown.

    Uses the built-in notebook parser - no external dependencies required.

    Args:
        content: Raw notebook JSON string
        filename: The notebook filename

    Returns:
        Text representation of the notebook with code and markdown cells
    """
    try:
        nb = loads_notebook(content)
        return notebook_to_text(nb, cell_type=None, separator="\n\n")
    except Exception:
        # If parsing fails, return raw content
        return content


class GithubRepositoryDataReader:
    """Downloads and parses files from a GitHub repository.

    Uses codeload.github.com to fetch repository archives without requiring git.

    Example:
        from gitsource import GithubRepositoryDataReader, notebook_processor

        reader = GithubRepositoryDataReader(
            repo_owner="alexeygrigorev",
            repo_name="gitsource",
            allowed_extensions={"md", "ipynb"},
            processors={"ipynb": notebook_processor},
        )
        files = reader.read()
    """

    def __init__(
        self,
        repo_owner: str,
        repo_name: str,
        commit_id: str | None = None,
        branch: str = "main",
        allowed_extensions: Iterable[str] | None = None,
        filename_filter: Callable[[str], bool] | None = None,
        processors: dict[str, Processor] | None = None,
        skip_hidden: bool = False,
    ) -> None:
        """Initialize the GitHub repository data reader.

        Args:
            repo_owner: The owner/organization of the GitHub repository
            repo_name: The name of the GitHub repository
            commit_id: Optional commit SHA (full or short) to fetch. When set,
                the archive for that exact commit is downloaded and branch is
                ignored. This pins the data to an immutable revision.
            branch: The git branch to fetch (default: "main"). Used only when
                commit_id is not provided.
            allowed_extensions: Optional set of file extensions to include
                (e.g., {"md", "py"}). If not provided, all file types are included
            filename_filter: Optional callable to filter files by their path
            processors: Optional dict mapping file extensions to processor functions.
                Processors take (content, filename) and return processed content.
                Available: notebook_processor (for .ipynb files)
            skip_hidden: If True, skip hidden files (starting with .). Default: False
        """
        prefix = "https://codeload.github.com"
        if commit_id is not None:
            self.url = f"{prefix}/{repo_owner}/{repo_name}/zip/{commit_id}"
        else:
            self.url = f"{prefix}/{repo_owner}/{repo_name}/zip/refs/heads/{branch}"

        if allowed_extensions is not None:
            self.allowed_extensions = {ext.lower() for ext in allowed_extensions}
        else:
            self.allowed_extensions = None

        if filename_filter is None:
            self.filename_filter = lambda filepath: True
        else:
            self.filename_filter = filename_filter

        if processors is None:
            self.processors = {}
        else:
            self.processors = processors

        self.skip_hidden = skip_hidden

    def read(self) -> list[RawRepositoryFile]:
        """Download and extract files from the GitHub repository.

        Returns:
            List of RawRepositoryFile objects for each processed file

        Raises:
            Exception: If the repository download fails
        """
        resp = requests.get(self.url)
        if resp.status_code != 200:
            raise Exception(f"Failed to download repository: {resp.status_code}")

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        repository_data = self._extract_files(zf)
        zf.close()

        return repository_data

    def _extract_files(self, zf: zipfile.ZipFile) -> list[RawRepositoryFile]:
        """Extract and process files from the zip archive.

        Args:
            zf: ZipFile object containing the repository data

        Returns:
            List of RawRepositoryFile objects for each processed file
        """
        data = []

        for file_info in zf.infolist():
            filepath = self._normalize_filepath(file_info.filename)

            if self._should_skip_file(filepath):
                continue

            try:
                with zf.open(file_info) as f_in:
                    content = f_in.read().decode("utf-8", errors="ignore")
                    if content is None:
                        continue

                    content = content.strip()

                    # Apply processor if registered for this extension
                    ext = self._get_extension(filepath)
                    if ext in self.processors:
                        processor = self.processors[ext]
                        content = processor(content, filepath)

                    file = RawRepositoryFile(
                        filename=filepath,
                        content=content,
                    )
                    data.append(file)

            except Exception as e:
                raise Exception(f"Error processing {file_info.filename}: {e}") from e

        return data

    def _should_skip_file(self, filepath: str) -> bool:
        """Determine whether a file should be skipped during processing.

        Args:
            filepath: The file path to check

        Returns:
            True if the file should be skipped, False otherwise
        """
        filepath = filepath.lower()

        # Skip directories
        if filepath.endswith("/"):
            return True

        # Skip hidden files
        if self.skip_hidden:
            filename = filepath.split("/")[-1]
            if filename.startswith("."):
                return True

        # Filter by extension
        if self.allowed_extensions:
            ext = self._get_extension(filepath)
            if ext not in self.allowed_extensions:
                return True

        # Apply custom filter
        if not self.filename_filter(filepath):
            return True

        return False

    def _get_extension(self, filepath: str) -> str:
        """Extract the file extension from a filepath.

        Args:
            filepath: The file path to extract extension from

        Returns:
            The file extension (without dot) or empty string if no extension
        """
        filename = filepath.lower().split("/")[-1]
        if "." in filename:
            return filename.rsplit(".", maxsplit=1)[-1]
        return ""

    def _normalize_filepath(self, filepath: str) -> str:
        """Removes the top-level directory from the file path inside the zip archive.

        'repo-main/path/to/file.py' -> 'path/to/file.py'

        Args:
            filepath: The original filepath from the zip archive

        Returns:
            The normalized filepath with top-level directory removed
        """
        parts = filepath.split("/", maxsplit=1)
        return parts[1] if len(parts) > 1 else parts[0]
