from __future__ import annotations
from typing import List, Annotated
from ..utils.shell import run_shell
from ..utils.fs import write_json, stage_program
from ..orchestration.schemas import CompilerAnalysisInput, CompilerAnalysisOutput
from .base import Tool
from pathlib import Path
import uuid, re

def parse_ptxas(stderr:str):
    parsed = {}
    # Example: ptxas info    : Used 32 registers, 256 bytes smem, 0 bytes cmem[0]
    m = re.search(r"Used\s+(\d+)\s+registers", stderr)
    if m: parsed["registers"] = int(m.group(1))
    m = re.search(r"(\d+)\s+bytes smem", stderr)
    if m: parsed["smem_bytes"] = int(m.group(1))
    m = re.search(r"(\d+)\s+bytes cmem\[0\]", stderr)
    if m: parsed["cmem0_bytes"] = int(m.group(1))
    return parsed

class CompilerAnalysisTool(Tool):
    name = "compiler_analysis"
    description = "Compile code with analysis flags and parse resource usage (registers, smem, etc.). This is a standalone file, so include a main function or compile with -c."
    input_schema = CompilerAnalysisInput
    output_schema = CompilerAnalysisOutput

    def __init__(self, cfg):
        self.cfg = cfg

    def register_mcp_tool(self, mcp):
        @mcp.tool(name=self.name, description=self.description)
        def compiler_analysis(
            code: Annotated[str, "Source code to pass to compiler."],
            compiler_cmd: Annotated[str, "Compiler command to run."],
            flags: Annotated[List[str], "Compiler flags to use."]
        ) -> str:
            return self.run(code=code, compiler_cmd=compiler_cmd, flags=flags)

    def _run(self, **kwargs):
        inp = self.input_schema(**kwargs)
        run_id = f"comp-{uuid.uuid4().hex[:8]}"
        run_dir = self.cfg.workdir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        stage_dir = stage_program(self.cfg.program_dir, run_dir)

        src = stage_dir / "_analysis.cu"
        src.write_text(inp.code)

        cmd = inp.compiler_cmd
        if inp.flags:
            cmd = cmd + " " + " ".join(inp.flags)
        cmd = cmd + " " + "_analysis.cu"
        res = run_shell(cmd, cwd=str(stage_dir), env={"CUDA_VISIBLE_DEVICES": self.cfg.gpu_ids}, timeout_s=self.cfg.timeout_s)
        parsed = parse_ptxas(res.stderr)
        out = self.output_schema(success=(res.returncode==0), returncode=res.returncode, stdout=res.stdout[-8000:], stderr=res.stderr[-8000:], parsed=parsed, error=None if res.returncode==0 else "compile_failed")
        write_json(run_dir / "compiler_analysis_result.json", out.model_dump())
        return str(out.model_dump())
