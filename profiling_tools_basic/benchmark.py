from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Annotated
import json, os, uuid, textwrap, re
from pydantic import Field

from ..utils.shell import run_shell
from ..utils.fs import stage_program, write_json, safe_read_text
from ..orchestration.patches import apply_roi_patch_file
from ..orchestration.schemas import BenchmarkInput, BenchmarkOutput
from .base import Tool

def parse_metrics_from_stdout(stdout:str) -> Dict[str, Any]:
    stdout = stdout.strip().removesuffix("logout")
    # Support either a pure JSON payload or a line like: JSON: { ... }
    m = re.search(r'\{[\s\S]*\}\s*$', stdout.strip())
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    m = re.search(r'JSON:\s*(\{[\s\S]*\})', stdout)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return {}

class BenchmarkTool(Tool):
    name = "benchmark_code"
    description = "Patch ROI with provided code and run user's benchmark script. Returns timings and correctness."
    input_schema = BenchmarkInput
    output_schema = BenchmarkOutput

    def __init__(self, cfg):
        self.cfg = cfg

    def register_mcp_tool(self, mcp):
        @mcp.tool(name=self.name, description=self.description)
        def benchmark(
            modified_kernel: Annotated[str, "The modified region of interest. Will directly replace the ROI in the code. Leave empty to use the original code."], 
            compile_args: Annotated[str, "Additional compile arguments to pass to the benchmark script."] = "", 
            extra_env: Annotated[Dict[str, Any], "Additional environment variables to set for the benchmark script."] = Field(default_factory=dict)
        ) -> Dict[str, Any]:
            return self.run(modified_kernel=modified_kernel, compile_args=compile_args, extra_env=extra_env)

    def _run(self, **kwargs) -> Dict[str, Any]:
        inp = self.input_schema(**kwargs)
        run_id = f"bench-{uuid.uuid4().hex[:8]}"
        run_dir = self.cfg.workdir / run_id
        stage_dir = run_dir / "stage"
        run_dir.mkdir(parents=True, exist_ok=True)
        stage_program(self.cfg.program_dir, run_dir)

        # Apply patch to staged file
        target_file = stage_dir / self.cfg.file

        if inp.modified_kernel != "":
            apply_roi_patch_file(target_file, self.cfg.start_line, self.cfg.end_line, inp.modified_kernel)

        env = dict(inp.extra_env)
        env.update({
            "EXTRA_COMPILE_ARGS": inp.compile_args,
            "CUDA_VISIBLE_DEVICES": self.cfg.gpu_ids,
            "ROI_FILE": str(self.cfg.file),
            "ROI_START_LINE": str(self.cfg.start_line),
            "ROI_END_LINE": str(self.cfg.end_line),
            "GPU_OPT_RUN_ID": run_id,
        })
        env.update(self.cfg.env_vars)
        print(env)

        # Ensure script path relative to original cwd
        script_path = (self.cfg.script if self.cfg.script.is_absolute() else (self.cfg.program_dir / self.cfg.script)).resolve()
        if not script_path.exists():
            return self.output_schema(success=False, returncode=127, error=f"Script not found: {script_path}", artifacts_dir=str(run_dir)).model_dump()

        # Copy script into stage dir for reproducible relative paths
        stage_script = stage_dir / script_path.name
        if script_path != stage_script:
            stage_script.write_text(script_path.read_text())
            os.chmod(stage_script, 0o755)

        res = run_shell(f"./{stage_script.name} \"$EXTRA_COMPILE_ARGS\"", cwd=str(stage_dir), env=env, timeout_s=self.cfg.timeout_s)
        metrics = parse_metrics_from_stdout(res.stdout)

        out = self.output_schema(
            success=(res.returncode == 0),
            returncode=res.returncode,
            correctness=metrics.get("correct"),
            time=metrics.get("time"),
            stdout_tail=res.stdout[-4000:],
            artifacts_dir=str(run_dir),
            compile_args=inp.compile_args,
            error=None if res.returncode == 0 else res.stderr[-4000:],
        )
        write_json(run_dir / "benchmark_result.json", out.model_dump())
        return out.model_dump()
