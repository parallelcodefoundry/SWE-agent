---
name: openhands
description: "OpenHands (formerly OpenDevin) agent framework. Use when user mentions 'openhands', 'opendevin', 'CodeActAgent', OpenHands sandbox, TOML config, or headless agent execution."
---

# OpenHands (formerly OpenDevin)

## Source Location

- **Local clone:** `/pscratch/sd/k/krydzy/swefficiency/OpenHands/`
- **Main repo:** https://github.com/All-Hands-AI/OpenHands
- **Documentation:** https://docs.openhands.dev/

## Quick Start

```bash
# Install (use the sweagent venv on Perlmutter)
source ~/envs/sweagent/bin/activate
pip install openhands

# Headless mode (for automation/eval)
openhands --headless -t "Your task here"
openhands --headless -f task.txt --json    # JSONL output
```

## Configuration (TOML)

Config file: `config.toml`. Key sections:

- **`[sandbox]`**: `base_container_image`, `enable_gpu`, `runtime_extra_deps`, `volumes`, `timeout`
- **`[llm]`**: `model` (litellm format), `api_key`, `base_url`, `max_input_tokens`, `native_tool_calling`
- **`[agent]`**: `enable_browsing`, `enable_jupyter`, `enable_cmd`, `enable_editor`, `enable_think`
- **`[core]`**: `default_agent = "CodeActAgent"`, `runtime` (docker|local|remote|kubernetes), `max_iterations`, `max_budget_per_task`

## Perlmutter Setup

- **Use `runtime = "local"`** -- Perlmutter uses `podman-hpc`, not Docker. Local runtime gives direct GPU/module access.
- **Module system is host-only** -- Cray modules are inaccessible from containers.
- **GPU access**: A100s only available on compute nodes inside `salloc`/`sbatch`.

```bash
# On a compute node
module load python cmake openmpi/5.0.7 cuda/12.4
source ~/envs/openhands/bin/activate
export PATH=/pscratch/sd/k/krydzy/SWE-agent/tools/kripke_harness/bin:$PATH
export KRIPKE_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Kripke_test

openhands --headless -t "Optimize Kripke for A100 GPUs.
Available tools: kripke_build --arch CUDA, kripke_run --arch CUDA."
```

## Critical Perlmutter Fixes (Validated)

1. **tmux 3.1c lacks `-e` flag**: Built tmux 3.5a at `~/local/bin/tmux`. OpenHands launcher prepends to PATH.
2. **tmux "command too long"**: `openhands_runner.py` strips bulky SLURM/Cray env vars before SDK init.
3. **`module load python` shadows venv**: Load modules BEFORE activating venv.
4. **openhands.py shadows pip openhands**: Invoke via `python -m batch.frameworks.openhands_runner`.
5. **pip openhands v1.2.1 is SDK/TUI only**: No `openhands.core.main`. Use SDK runner approach.

## Common Issues

1. **Docker vs Podman**: Use `runtime = "local"` or create a podman wrapper script.
2. **GPU contention**: If running vLLM + benchmarks on same node, use TP=2 for vLLM.
3. **litellm model names**: Use litellm format; for local vLLM: `openai/openai/MODEL_NAME`.
4. **V0 deprecation (April 2026)**: Legacy eval APIs will be removed; plan migration to Agent SDK.

For detailed reference, see references/ in this skill directory.
