import os
from pathlib import Path
from typing import Optional, Dict, Any


class FileToolkit:
    """文件操作工具集，供 LangChain Agent 调用。"""

    def __init__(self, project_root: str):
        normalized_root = project_root.replace("\\", "/")
        self.project_root = Path(normalized_root).resolve()
        if not self.project_root.exists() or not self.project_root.is_dir():
            raise FileNotFoundError(f"项目根目录不存在: {project_root}")

    def _resolve_path(self, relative_path: str) -> Path:
        normalized = relative_path.replace("\\", "/")
        full_path = (self.project_root / normalized).resolve()

        if not str(full_path).startswith(str(self.project_root)):
            raise PermissionError(
                f"禁止访问项目根目录以外的路径: {relative_path}"
            )
        return full_path

    def read_file(self, relative_path: str, line_start: int = None, line_end: int = None) -> Dict[str, Any]:
        """读取文件内容，可选指定行号范围。

        Args:
            relative_path: 相对于项目根目录的文件路径
            line_start: 起始行号（1-based，包含）
            line_end: 结束行号（1-based，包含）
        """
        try:
            file_path = self._resolve_path(relative_path)
            if not file_path.exists():
                return {"success": False, "error": f"文件不存在: {relative_path}"}
            if not file_path.is_file():
                return {"success": False, "error": f"路径不是文件: {relative_path}"}

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            total_lines = len(lines)

            if line_start is not None and line_end is not None:
                start = max(0, line_start - 1)
                end = min(total_lines, line_end)
                content = "".join(lines[start:end])
                actual_start = start + 1
                actual_end = end
            else:
                content = "".join(lines)
                actual_start = 1
                actual_end = total_lines

            return {
                "success": True,
                "file_path": relative_path,
                "line_start": actual_start,
                "line_end": actual_end,
                "total_lines": total_lines,
                "content": content,
            }
        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"读取文件失败: {str(e)}"}

    def write_file(self, relative_path: str, content: str, backup: bool = True) -> Dict[str, Any]:
        """写入文件内容，覆盖原文件。

        Args:
            relative_path: 相对于项目根目录的文件路径
            content: 要写入的完整文件内容
            backup: 是否创建 .bak 备份文件
        """
        try:
            file_path = self._resolve_path(relative_path)
            if not file_path.exists():
                return {"success": False, "error": f"文件不存在: {relative_path}"}

            if backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".bak")
                with open(file_path, "rb") as src:
                    with open(backup_path, "wb") as dst:
                        dst.write(src.read())

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "file_path": relative_path,
                "backup_created": backup,
                "backup_path": str(backup_path) if backup else None,
                "bytes_written": len(content),
            }
        except PermissionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"写入文件失败: {str(e)}"}

    def replace_lines(
        self,
        relative_path: str,
        line_start: int,
        line_end: int,
        new_content: str,
        backup: bool = True,
    ) -> Dict[str, Any]:
        """替换文件中指定行范围的内容。

        Args:
            relative_path: 相对于项目根目录的文件路径
            line_start: 起始行号（1-based，包含）
            line_end: 结束行号（1-based，包含）
            new_content: 替换后的新内容（字符串，可包含多行）
            backup: 是否创建备份
        """
        try:
            file_path = self._resolve_path(relative_path)
            if not file_path.exists():
                return {"success": False, "error": f"文件不存在: {relative_path}"}

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            total_lines = len(lines)
            start_idx = max(0, line_start - 1)
            end_idx = min(total_lines, line_end)

            if start_idx >= total_lines:
                return {"success": False, "error": f"起始行号 {line_start} 超出文件总行数 {total_lines}"}

            new_lines = new_content.splitlines(keepends=True)
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"

            modified_lines = lines[:start_idx] + new_lines + lines[end_idx:]
            modified_content = "".join(modified_lines)

            return self.write_file(relative_path, modified_content, backup=backup)
        except Exception as e:
            return {"success": False, "error": f"替换行失败: {str(e)}"}

    def list_dir(self, relative_path: str = ".") -> Dict[str, Any]:
        """列出目录内容。"""
        try:
            dir_path = self._resolve_path(relative_path)
            if not dir_path.is_dir():
                return {"success": False, "error": f"不是目录: {relative_path}"}

            items = []
            for item in sorted(dir_path.iterdir()):
                items.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "path": str(item.relative_to(self.project_root)).replace("\\", "/"),
                })

            return {
                "success": True,
                "dir_path": relative_path,
                "items": items,
            }
        except Exception as e:
            return {"success": False, "error": f"列出目录失败: {str(e)}"}
