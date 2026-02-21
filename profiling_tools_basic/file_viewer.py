from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional, Annotated
import json, os, uuid, textwrap, re
from pydantic import Field

from ..utils.shell import run_shell
from ..utils.fs import stage_program, write_json, safe_read_text
from ..orchestration.patches import apply_roi_patch_file
from ..orchestration.schemas import FileViewerInput, FileViewerOutput
from .base import Tool


class FileViewerTool(Tool):
    name = "file_viewer"
    description = "View parts of a file or the entire file"
    input_schema = FileViewerInput
    output_schema = FileViewerOutput

    def __init__(self, cfg):
        self.cfg = cfg

    
    def register_mcp_tool(self, mcp):
        @mcp.tool(name=self.name, description=self.description)
        def file_viewer(
            file_path: Annotated[str, "The path to the file to view"],
            start_line: Annotated[Optional[int], "The line to start viewing from. Omit for beginning of file."] = None,
            num_lines: Annotated[Optional[int], "The number of lines to view. Maximum of 100 lines. Defaults to 100 if omitted."] = None,
            include_line_numbers: Annotated[bool, "Whether to include line numbers in the output"] = False
        ) -> str:
            return self.run(file_path=file_path, start_line=start_line, num_lines=num_lines, include_line_numbers=include_line_numbers)


    def _run(self, **kwargs) -> str:
        inp = self.input_schema(**kwargs)
        root = self.cfg.program_dir
        file_path = root / inp.file_path

        if not file_path.exists():
            return f"Error: File not found {file_path}"
        
        if not file_path.is_file() or not os.access(file_path, os.R_OK):
            return f"Error: File is not readable {file_path}"

        num_lines_in_file_path = sum(1 for _ in file_path.read_text().splitlines())
        start_line = inp.start_line or 1
        num_lines = max(min(inp.num_lines or 100, 100), 1) # clamp to [1, 100]
        end_line = min(start_line + num_lines - 1, num_lines_in_file_path)

        if start_line >= end_line:
            return f"Error: Invalid line range {start_line}-{end_line} for file {file_path}"
        
        # get lines of file and return
        lines = file_path.read_text().splitlines()
        if inp.include_line_numbers:
            content = "\n".join(f"{i+start_line:6d}: {line}" for i, line in enumerate(lines[start_line-1:end_line]))
        else:
            content = "\n".join(lines[start_line-1:end_line])

        # for now, to solve the problem of some files with really long lines
        # we hard limit to 5k characters total
        if len(content) > 5000:
            content = content[:5000] + "\n...[truncated]..."

        return content
