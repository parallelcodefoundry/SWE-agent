from __future__ import annotations
from pathlib import Path
import os, uuid

from ..utils.shell import run_shell
from ..utils.fs import stage_program, write_json
from ..orchestration.patches import apply_roi_patch_file
from ..orchestration.schemas import ProfileInput, ProfileOutput
from .base import Tool

class ProfileTool(Tool):
    name = "profile_code"
    description = "Patch ROI and run under profiler or user script for counters."
    input_schema = ProfileInput
    output_schema = ProfileOutput

    def __init__(self, cfg):
        self.cfg = cfg

    def _run(self, **kwargs):
        inp = self.input_schema(**kwargs)
        run_id = f"profile-{uuid.uuid4().hex[:8]}"
        run_dir = self.cfg.workdir / run_id
        stage_dir = run_dir / "stage"
        run_dir.mkdir(parents=True, exist_ok=True)
        stage_program(self.cfg.program_dir, run_dir)

        target_file = stage_dir / self.cfg.file
        apply_roi_patch_file(target_file, self.cfg.start_line, self.cfg.end_line, inp.modified_kernel)

        env = dict(inp.extra_env)
        env.update({
            "EXTRA_COMPILE_ARGS": inp.compile_args,
            "CUDA_VISIBLE_DEVICES": self.cfg.gpu_ids,
            "PROFILE_COUNTERS": ",".join(inp.counters or self.cfg.ncu_metrics),
            "ROI_FILE": str(self.cfg.file),
            "ROI_START_LINE": str(self.cfg.start_line),
            "ROI_END_LINE": str(self.cfg.end_line),
            "GPU_OPT_RUN_ID": run_id,
        })

        script = (self.cfg.profile_script or self.cfg.script)
        script_path = (script if script.is_absolute() else (self.cfg.program_dir / script)).resolve()
        if not script_path.exists():
            return self.output_schema(success=False, returncode=127, error=f"Script not found: {script_path}", artifacts_dir=str(run_dir)).model_dump()

        stage_script = stage_dir / script_path.name
        if script_path != stage_script:
            stage_script.write_text(script_path.read_text())
            os.chmod(stage_script, 0o755)

        res = run_shell(f"./{stage_script.name} \"$EXTRA_COMPILE_ARGS\"", cwd=str(stage_dir), env=env, timeout_s=self.cfg.timeout_s)
        out = self.output_schema(
            success=(res.returncode == 0),
            returncode=res.returncode,
            stdout=res.stdout[-12000:],
            stderr=res.stderr[-12000:],
            artifacts_dir=str(run_dir),
            error=None if res.returncode == 0 else res.stderr[-4000:]
        )
        write_json(run_dir / "profile_result.json", out.model_dump())
        return out.model_dump()
