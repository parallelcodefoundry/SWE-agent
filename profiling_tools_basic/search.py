from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional, Annotated
import json, os, uuid, textwrap, re
from pydantic import Field

from ..utils.shell import run_shell
from ..utils.fs import stage_program, write_json, safe_read_text
from ..orchestration.patches import apply_roi_patch_file
from ..orchestration.schemas import SearchInput, SearchOutput
from .base import Tool


class SearchTool(Tool):
    name = "search"
    description = "search for substrings in the project"
    input_schema = SearchInput
    output_schema = SearchOutput

    def __init__(self, cfg):
        self.cfg = cfg

    
    def register_mcp_tool(self, mcp):
        @mcp.tool(name=self.name, description=self.description)
        def search(
            substring: Annotated[str, "The substring to search for"],
            is_regex: Annotated[bool, "Whether the substring is a regex pattern to find matches for."] = False,
            context_length: Annotated[int, "Number of context lines to include before and after each match. Integer between 0 and 3, inclusive."] = 0,
            max_results: Annotated[int, "Maximum number of results to return. Integer between 1 and 20."] = 20,
        ) -> str:
            return self.run(substring=substring, is_regex=is_regex, context_length=context_length, max_results=max_results)


    def _run(self, **kwargs) -> str:
        inp = self.input_schema(**kwargs)

        # validate inputs
        if not (0 <= inp.context_length <= 3):
            return "Invalid context_length. Must be integer between 0 and 3."

        if not (1 <= inp.max_results <= 20):
            return "Invalid max_results. Must be integer between 1 and 20."
        
        # find all matches
        matches = []
        if inp.is_regex:
            pattern = re.compile(inp.substring)
        else:
            pattern = re.compile(re.escape(inp.substring))

        for root, _, files in os.walk(self.cfg.program_dir):
            if len(matches) >= inp.max_results:
                break

            for file in files:
                if len(matches) >= inp.max_results:
                    break

                file_path = Path(root) / file
                try:
                    with open(file_path, "r") as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            for match in pattern.finditer(line):
                                start_line = max(0, i - inp.context_length)
                                end_line = min(len(lines), i + inp.context_length + 1)
                                matches.append({
                                    "file": str(file_path.relative_to(self.cfg.program_dir)),
                                    "line": i + 1,
                                    "match": line[match.start():match.end()],
                                    "context": "\n".join(lines[start_line:end_line])
                                })
                except Exception as e:
                    continue


        # limit results
        matches = matches[:inp.max_results]

        # for sake of token limits, truncate each line to 200 characters
        for match in matches:
            match["context"] = "\n".join(list(map(lambda l: l if len(l) <= 200 else l[:200] + "...[truncated]...", match["context"].splitlines())))

        # format as `match {match_no} in {file} at line {line}: {content}`
        content = ""
        for i, match in enumerate(matches):
            content += f"match {i+1} in {match['file']} at line {match['line']}: {match['match']}\n"
            content += f"{match['context']}\n\n"

        return content
