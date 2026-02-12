---
name: openhands
description: "Knowledge about the Openhands (formerly OpenDevin) agentic framework including benchmark instance configuration, sandbox environment setup, evaluation harness, and result collection. Load when creating or modifying Openhands benchmarks."
---

# OpenHands (formerly OpenDevin)

## Source Location

- **Local clone:** `/pscratch/sd/k/krydzy/swefficiency/OpenHands/`
- **Main repo:** https://github.com/All-Hands-AI/OpenHands
- **Benchmarks repo:** https://github.com/OpenHands/benchmarks
- **Agent SDK:** https://github.com/OpenHands/software-agent-sdk
- **Documentation:** https://docs.openhands.dev/

## Architecture Overview

The CodeActAgent runs inside an isolated runtime (Docker by default, also local/remote/K8s) and interacts with code via bash, IPython, file editing, and web browsing tools. A controller orchestrates the loop: agent emits Actions, the runtime executes them, Observations are returned, and the agent continues. Configuration uses TOML format with environment variable overrides.

## Agent Tools (CodeActAgent)

| Tool | Action Type | Description |
|------|-------------|-------------|
| `execute_bash` | `CmdRunAction` | Run bash commands; handles long-running, background, timeout |
| `execute_ipython_cell` | `IPythonRunCellAction` | Run Python in IPython; supports `%pip`, persistent vars |
| `str_replace_editor` | `FileEditAction` | View/create/edit files via exact string replacement |
| `edit_file` | `FileEditAction` | LLM-based file editing (disabled by default) |
| `web_read` / `browser` | `BrowseURLAction` | Read/interact with web pages |
| `think` | `AgentThinkAction` | Scratchpad for reasoning (no execution) |
| `finish` | `AgentFinishAction` | Signal task completion |

Tools toggled via agent config: `enable_browsing`, `enable_jupyter`, `enable_cmd`, `enable_llm_editor`, `enable_editor`. Custom tools via MCP servers or `function_calling.py`.

## Configuration Format

Configuration uses TOML (`config.toml`). See `config.template.toml` in the OpenHands repo for full reference.

**Sandbox** (`[sandbox]`): `base_container_image`, `runtime_container_image`, `enable_gpu`, `cuda_visible_devices`, `runtime_extra_deps`, `runtime_startup_env_vars`, `volumes`, `timeout`.

**LLM** (`[llm]`): `model` (litellm format), `api_key`, `base_url`, `temperature`, `max_input_tokens`, `max_output_tokens`, `native_tool_calling`. Multiple configs via `[llm.secondary]`.

**Agent** (`[agent]`): `enable_browsing`, `enable_jupyter`, `enable_cmd`, `enable_editor`, `enable_think`. Agent-specific overrides in `[agent.CodeActAgent]`.

**Core** (`[core]`): `default_agent = "CodeActAgent"`, `runtime` (docker|local|remote|kubernetes), `max_iterations`, `max_budget_per_task`, `workspace_base`, `save_trajectory_path`.

## Running OpenHands

```bash
# Install (use the sweagent venv on Perlmutter)
source ~/envs/sweagent/bin/activate
pip install openhands          # or: uv tool install openhands --python 3.12

# Interactive GUI (port 3000)
openhands serve --gpu --mount-cwd

# Headless mode (no UI, for automation/eval)
openhands --headless -t "Your task here"
openhands --headless -f task.txt --json    # JSONL output for programmatic parsing
```

Headless mode runs in always-approve mode (no confirmation prompts), suitable for CI/CD and evaluation.

## Key Differences from SWE-agent

| Aspect | SWE-agent | OpenHands |
|--------|-----------|-----------|
| **Runtime** | Bash subprocess (local) or Docker | Docker (default), local/remote/K8s |
| **Agent interface** | Text-based tool calls parsed from output | Native function calling via litellm |
| **Tool system** | YAML config + shell scripts in `bin/` | Python tool defs in `function_calling.py` |
| **Custom tools** | Add YAML + shell script to `tools/` | Modify `function_calling.py` or MCP servers |
| **Task input** | YAML config with Jinja2 templates | TOML config + headless `-t` flag or programmatic API |
| **Prompt control** | Jinja2 `system_template`, `instance_template` | Prompts in `prompts/` dir; microagents for customization |
| **File editing** | `str_replace_editor` (Anthropic-style) | Same `str_replace_editor` or `edit_file` (LLM-based) |
| **Evaluation** | In-repo (`sweagent run`, batch scripts) | Separate `OpenHands/benchmarks` repo |
| **History mgmt** | `last_n_observations` processor | Condensers: noop, observation_masking, recent, llm, amortized |
| **Cost control** | `per_instance_cost_limit` in model config | `max_budget_per_task` in core config |
| **Parallelism** | `num_workers` in batch config | `--num-workers` CLI flag + remote workspace |

### HPC Benchmark Implications

1. **No shell-script tool bundles:** Our harness scripts (`kripke_build`, `kripke_run`, etc.) are placed in the sandbox and called via `execute_bash` (simplest approach).
2. **Docker is default:** For Perlmutter, use `runtime="local"` for direct GPU/module access, or `podman-hpc` with a wrapper.
3. **Evaluation is separate:** Would need `benchmarks/benchmarks/hpc/` following the SWE-bench pattern.
4. **No Jinja2 templates:** All context must be in the initial task string or discoverable by the agent.

## Perlmutter Considerations

- **Container runtime:** Perlmutter uses `podman-hpc`, not Docker. Use `runtime = "local"` (recommended) to bypass containers entirely, or create a `$HOME/bin/docker` wrapper pointing to `podman-hpc`.
- **GPU access:** With local runtime, GPUs are directly accessible (no passthrough needed). A100s only available on compute nodes -- must run inside `salloc`/`sbatch`.
- **Module system:** Cray modules (`module load cuda/12.4 openmpi/5.0.7`) are host-only and inaccessible from containers. This is a strong reason to use local runtime.
- **Network:** Compute nodes have limited outbound. Route LLM API calls through a local vLLM server.

## Setting Up HPC Benchmark (Headless CLI)

Use OpenHands headless mode with local runtime, harness scripts in PATH:

```bash
# On a compute node
module load python cmake openmpi/5.0.7 cuda/12.4
source ~/envs/openhands/bin/activate

# Set up environment
export PATH=/pscratch/sd/k/krydzy/SWE-agent/tools/kripke_harness/bin:$PATH
export KRIPKE_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Kripke_test

# Run OpenHands in headless mode
openhands --headless -t "$(cat <<'EOF'
Optimize the runtime performance of the Kripke 3D Sn deterministic transport application.
The application is in /pscratch/sd/k/krydzy/SWE-agent/Kripke_test.

IMPORTANT: You are optimizing for NVIDIA A100 GPUs.

Available tools (run as bash commands):
- kripke_build --arch CUDA     Build the application
- kripke_run --arch CUDA       Run and measure performance + correctness

WORKFLOW:
1. Build with: kripke_build --arch CUDA
2. Run baseline: kripke_run --arch CUDA
3. Explore code, identify optimizations
4. Edit source files
5. Rebuild: kripke_build --arch CUDA
6. Test: kripke_run --arch CUDA
EOF
)"
```

For programmatic evaluation, see `openhands.core.main` (`run_controller` API). For the benchmarks repo pattern, see `OpenHands/benchmarks`. For result format mapping, see `agent_docs/experiment-workflow.md`.

## Common Issues

1. **Docker vs Podman on Perlmutter:** Use `runtime = "local"` or create a podman wrapper script.
2. **No module system in containers:** Cray modules are host-only; local runtime avoids this.
3. **GPU contention:** If running vLLM + benchmarks on same node, use TP=2 for vLLM to leave GPUs free.
4. **litellm model names:** Use litellm format, e.g. `openai/gpt-4o`, `anthropic/claude-sonnet-4-5-20250929`; for local vLLM: `openai/openai/MODEL_NAME`.
5. **V0 deprecation (April 2026):** Legacy eval APIs in `openhands.core.main` will be removed; plan migration to Agent SDK.
