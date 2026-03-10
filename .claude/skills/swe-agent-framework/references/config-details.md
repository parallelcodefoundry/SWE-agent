# SWE-agent Configuration Details

## Config Override Syntax

CLI overrides use dotted notation, applied after YAML loading:
```bash
--agent.model.name "openai/openai/gpt-oss-120b"
--agent.model.per_instance_cost_limit 0
--env.repo.path /path/to/repo
--agent.tools.execution_timeout 600
```

Configs use Pydantic BaseSettings with YAML files. Env vars with prefix `SWE_AGENT_` override any field. Multiple `--config` files merge in order. See `config/hpc/kripke_no_profiling.yaml` for full config structure.

## Model Name Patterns

SWE-agent uses litellm for model routing:

| Pattern | Backend | Example | Notes |
|---------|---------|---------|-------|
| `openai/MODEL` | OpenAI API | `openai/gpt-4o` | Standard OpenAI |
| `openai/openai/MODEL` | OpenAI-compatible | `openai/openai/gpt-oss-120b` | **Double prefix needed for vLLM** |
| `hosted_vllm/MODEL` | Hosted vLLM | `hosted_vllm/gpt-oss-120b` | Alternative to double-openai |
| `ollama_chat/MODEL` | Ollama | `ollama_chat/swe-agent-32b` | Local Ollama |
| `anthropic/MODEL` | Anthropic | `anthropic/claude-3-5-sonnet` | Anthropic API |

**Critical:** The double `openai/openai/` prefix is required for vLLM's OpenAI-compatible endpoint. First `openai/` tells litellm the provider, second is part of the model name vLLM expects.

## Tool Bundle Format

```
tools/{name}/
  config.yaml     # Tool definitions (tools: {name: {signature, docstring, arguments}})
  bin/             # Executable scripts
  lib/             # Optional shared libraries
  install.sh       # Optional install script
```

`config.yaml` skeleton:
```yaml
execution_timeout: 600
tools:
  tool_name:
    signature: "tool_name [<arg1>]"
    docstring: "Description the agent sees."
    arguments:
      - name: arg1
        type: string
        description: "What this argument does"
        required: false
        argument_format: "--flag {{value}}"
```

## Config Variants: no_profiling vs with_profiling

The only differences in `{app}_with_profiling.yaml`:
1. **Extra bundles**: `hpctoolkit`, `hatchet`, `system_info`, `profiling`
2. **Instance template** mentions profiling tools and adds "PROFILING TOOLS AVAILABLE" note
3. **Prerequisites** include spack/HPCToolkit loading

Profiling bundles: `hpctoolkit` (hpc_profile), `hatchet` (hatchet_analyze), `profiling` (benchmark_code, compiler_analysis, microbench_code), `system_info` (gpu_info, cpu_info, memory_info, etc.).

## Framework Modifications (local branch)

1. **`sweagent/agent/agents.py`** -- `LocalRepoConfig` support; patches write to `/tmp/sweagent/model.patch`
2. **`sweagent/environment/swe_env.py`** -- Skips repo copying for local repos; uses `repo.path.resolve()`
3. **`sweagent/tools/tools.py`** -- Configurable `tools_base_path`; all `/root/` refs replaced with `{base_path}/`
4. **`sweagent/agent/models.py`** -- Extracts `reasoning_content` from vLLM responses
5. **`sweagent/tools/parsing.py`** -- Strips `<|channel|>` suffix, fallback JSON parsing (3 formats), command aliases (`str_replace`->`str_replace_editor`, `execute_bash`->`bash`, `finish`->`submit`), auto-submit on unparseable actions

## Multi-Node Execution

`run_benchmark.sh` auto-calculates nodes: N apps + 1 vLLM (or N with `--external-model`). Each app gets a dedicated node via `srun --exclusive`. vLLM on node 0, apps on nodes 1..N.

### External Model Support
```bash
source ~/.openai_env  # exports OPENAI_API_BASE and OPENAI_API_KEY
bash batch/run_benchmark.sh --base --external-model --model-name gpt-4o-mini
```
`--model-name` overrides config model name, strips `api_base`/`api_key`, sets `per_instance_cost_limit: 1.0`.

## Parse Function Types

SWE-agent supports 11 parse modes in `sweagent/tools/parsing.py`. Key ones:

| Type | How model sees tools | Tool call format | Best for |
|------|---------------------|-----------------|----------|
| `function_calling` | API function definitions (LiteLLM) | JSON tool_calls | OpenAI, most models |
| `xml_function_calling` | Text in system prompt | `<function=name><parameter=key>value</parameter></function>` | **Qwen models** |
| `thought_action` | Text in system prompt | Thought + triple-backtick code block | Models struggling with function calling |
| `json` | API function definitions | JSON | Alternative to function_calling |
| `xml_thought_action` | Text in system prompt | XML thought + `<command>` tags | Alternative XML format |

**Critical architectural difference**: When `use_function_calling` is `True` (only `function_calling` and `json`), tools are sent via LiteLLM API tool definitions. When `False`, tool docs are embedded in system prompt text.

**Qwen models**: Use `xml_function_calling`. Qwen natively emits `<function=name>` XML which this parser handles directly. The default `function_calling` mode sends tools via API but Qwen exhibits "analysis paralysis" — makes valid tool calls for reading but never produces edits.

The benchmark launcher (`sweagent.py`) auto-selects `xml_function_calling` for Qwen models via `_apply_parse_function_override()`.

## Full Known Issues List

1. **Double openai prefix**: vLLM models need `openai/openai/MODEL` (not `openai/MODEL`)
2. **TP=4 GPU contention**: vLLM uses all 4 A100s, so benchmark apps compete for GPU time
3. **Kripke submodules**: Disable `submodule.recurse` in `_test` repos, remove origin remote to prevent git hangs
4. **g++-12 required**: Lulesh/Quicksilver need `g++-12` -- nvcc incompatible with g++ 13 for `-std=c++11`
5. **Laghos shared deps**: mfem/hypre/metis are sibling dirs shared between pristine and `_test`
6. **Agent build corruption**: Agent sometimes switches GPU builds to OpenMP or breaks deps during git-history runs
7. **Hatchet "(0)" values**: Hot-path reporting shows zero values, confusing the agent
8. **Parser auto-submit**: Patched parser auto-submits on unparseable actions -- can cause premature submission
9. **tools_base_path**: Must be `/tmp/sweagent` for local deployment (not `/root`)
10. **SLURM paths**: `#SBATCH` directives resolve from `/var/spool/slurmd/`, not the submission directory
11. **Tool schema types**: Use `number` not `float` in tool argument types -- OpenAI rejects `float`, vLLM is lenient
12. **SWE-agent copies tools to `/tmp/sweagent/`**: Script-relative paths (`__file__`) break. Use `SWE_AGENT_ROOT` env var (injected by benchmark runner) to find pristine repos
13. **External model routing**: `run_agent()` shell script must read `OPENAI_API_BASE`/`OPENAI_API_KEY` from env (not hardcode vLLM values). Config `api_base`/`api_key` must be stripped so LiteLLM uses env vars
14. **MPI execution**: `kripke_run` uses `mpirun` (not `srun`) for MPI, avoiding nested srun hangs. `INSIDE_BATCH_RUN=1` env var signals batch mode.
