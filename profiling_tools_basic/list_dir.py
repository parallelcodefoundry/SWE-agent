from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional, Annotated
import json, os, uuid, textwrap, re
from pydantic import Field

from ..utils.shell import run_shell
from ..utils.fs import stage_program, write_json, safe_read_text
from ..orchestration.patches import apply_roi_patch_file
from ..orchestration.schemas import ListDirInput, ListDirOutput
from .base import Tool


class ListDirTool(Tool):
    name = "list_dir"
    description = "list files in a directory"
    input_schema = ListDirInput
    output_schema = ListDirOutput

    def __init__(self, cfg):
        self.cfg = cfg

    
    def register_mcp_tool(self, mcp):
        @mcp.tool(name=self.name, description=self.description)
        def list_dir(
            dir_path: Annotated[str, "The path to the directory to list"]
        ) -> str:
            return self.run(dir_path=dir_path)
        
    
    def _run(self, **kwargs) -> str:
        inp = self.input_schema(**kwargs)
        dir = self.cfg.program_dir / inp.dir_path

        if not dir.exists():
            return f"Error: Directory not found {dir}"
        
        if not dir.is_dir():
            return f"Error: Path is not a directory {dir}"
        
        if not os.access(dir, os.R_OK):
            return f"Error: Directory is not readable {dir}"

        files = [str(p.relative_to(self.cfg.program_dir)) for p in dir.iterdir()]
        content = "\n".join(files)
        return content
