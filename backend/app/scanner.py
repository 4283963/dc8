import os
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class CodeChunk:
    file_path: str
    content: str
    line_start: int
    line_end: int
    file_type: str


class CodeScanner:
    SUPPORTED_EXTENSIONS = {
        "java": [".java"],
        "cpp": [".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh"],
    }

    @staticmethod
    def normalize_path(path_str: str) -> str:
        """将路径字符串规范化为统一的正斜杠格式，避免 Windows 反斜杠导致的问题。"""
        return path_str.replace("\\", "/")

    def __init__(self, project_path: str, file_types: List[str] = None):
        normalized_path = self.normalize_path(project_path)
        self.project_path = Path(normalized_path)
        if not self.project_path.exists():
            raise FileNotFoundError(f"Project path not found: {project_path}")
        if not self.project_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {project_path}")
        self.file_types = file_types or ["java", "cpp"]
        self._extensions = self._collect_extensions()

    def _collect_extensions(self) -> List[str]:
        extensions = []
        for ft in self.file_types:
            if ft in self.SUPPORTED_EXTENSIONS:
                extensions.extend(self.SUPPORTED_EXTENSIONS[ft])
        return extensions

    def scan_files(self) -> List[Path]:
        files = []
        for ext in self._extensions:
            files.extend(self.project_path.rglob(f"*{ext}"))
        return sorted(files)

    def _chunk_file(self, file_path: Path, chunk_size: int = 80, overlap: int = 20) -> List[CodeChunk]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return []

        if not lines:
            return []

        chunks = []
        total_lines = len(lines)
        file_type = self._get_file_type(file_path)

        rel_path = file_path.relative_to(self.project_path).as_posix()

        if total_lines <= chunk_size:
            content = "".join(lines)
            chunks.append(
                CodeChunk(
                    file_path=rel_path,
                    content=content,
                    line_start=1,
                    line_end=total_lines,
                    file_type=file_type,
                )
            )
            return chunks

        start = 0
        while start < total_lines:
            end = min(start + chunk_size, total_lines)
            chunk_lines = lines[start:end]
            content = "".join(chunk_lines)
            chunks.append(
                CodeChunk(
                    file_path=rel_path,
                    content=content,
                    line_start=start + 1,
                    line_end=end,
                    file_type=file_type,
                )
            )
            if end == total_lines:
                break
            start = end - overlap

        return chunks

    def _get_file_type(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        for ft, exts in self.SUPPORTED_EXTENSIONS.items():
            if suffix in exts:
                return ft
        return "unknown"

    def chunk_all_files(self, chunk_size: int = 80, overlap: int = 20) -> Tuple[List[CodeChunk], int]:
        files = self.scan_files()
        all_chunks = []
        for file_path in files:
            chunks = self._chunk_file(file_path, chunk_size, overlap)
            all_chunks.extend(chunks)
        return all_chunks, len(files)
