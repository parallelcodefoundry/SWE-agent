from __future__ import annotations
from ..utils.shell import run_shell
from ..utils.fs import write_json
from ..orchestration.schemas import MicrobenchInput, MicrobenchOutput
from .base import Tool
from pathlib import Path
from typing import Annotated
import uuid, os, time

class MicrobenchTool(Tool):
    name = "microbench_code"
    description = "Compile and run a standalone code snippet for quick timing experiments."
    input_schema = MicrobenchInput
    output_schema = MicrobenchOutput

    def __init__(self, cfg):
        self.cfg = cfg

    def register_mcp_tool(self, mcp):
        @mcp.tool(name=self.name, description=self.description)
        def microbench_code(
            code: Annotated[str, "Complete code file."], 
            nvcc_args: Annotated[str, "Arguments passed to nvcc compiler"], 
            run_args: Annotated[str | None, "Arguments passed to the executable"], 
            repeat: int = 5, 
            timeout_s: int = 300
        ) -> str:
            return self.run(code=code, nvcc_args=nvcc_args, run_args=run_args, repeat=repeat, timeout_s=timeout_s)
    
    def _run(self, **kwargs):
        inp = self.input_schema(**kwargs)
        run_id = f"micro-{uuid.uuid4().hex[:8]}"
        run_dir = self.cfg.workdir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        src = run_dir / "snippet.cu"
        src.write_text(inp.code)

        compile_cmd = f"nvcc {inp.nvcc_args} snippet.cu -o a.out"
        compile_res = run_shell(compile_cmd, cwd=str(run_dir), env={"CUDA_VISIBLE_DEVICES": self.cfg.gpu_ids}, timeout_s=inp.timeout_s)
        if compile_res.returncode != 0:
            out = self.output_schema(success=False, returncode=compile_res.returncode, compile_stdout=compile_res.stdout, compile_stderr=compile_res.stderr, error="compile_failed")
            write_json(run_dir / "microbench_result.json", out.model_dump())
            return out.model_dump()

        timings = []
        run_cmd = f"./a.out {inp.run_args or ''}".strip()
        for i in range(max(1, inp.repeat)):
            t0 = time.time()
            run_res = run_shell(run_cmd, cwd=str(run_dir), env={"CUDA_VISIBLE_DEVICES": self.cfg.gpu_ids}, timeout_s=inp.timeout_s)
            dt = (time.time() - t0) * 1000.0
            timings.append(dt)
            if run_res.returncode != 0:
                out = self.output_schema(success=False, returncode=run_res.returncode, compile_stdout=compile_res.stdout, compile_stderr=compile_res.stderr, run_stdout=run_res.stdout, run_stderr=run_res.stderr, timings=timings, error="run_failed")
                write_json(run_dir / "microbench_result.json", out.model_dump())
                return out.model_dump()

        out = self.output_schema(success=True, returncode=0, compile_stdout=compile_res.stdout, compile_stderr=compile_res.stderr, run_stdout=run_res.stdout, run_stderr=run_res.stderr, timings=timings)
        write_json(run_dir / "microbench_result.json", out.model_dump())
        return out.model_dump()
