# APPEB Restructure Audit

Comprehensive audit for migrating from SWE-agent fork monorepo → standalone APPEB benchmark suite with framework submodules.

**Audited**: 2026-03-16
**Current repo**: `/pscratch/sd/k/krydzy/SWE-agent` (physical location; `/global/homes/k/krydzy/SWE-agent` is a symlink pointing here)
**Git remotes**: `origin` → `parallelcodefoundry/SWE-agent`, `upstream` → `SWE-agent/SWE-agent`, `personal` → `KlaudiuszRydzy/swe-agent-testing`
**Active branch**: `dev` (primary working branch); `main` tracks upstream SWE-agent

---

## 1. File & Directory Classification

### Legend
- **(a)** SWE-agent core — stays in the fork/submodule
- **(b)** Benchmark infrastructure — moves to APPEB top-level
- **(c)** Framework-agnostic tooling/configs — shared by multiple frameworks
- **(d)** Unclear / needs input

---

### Top-Level Files

| File | Class | Notes |
|------|-------|-------|
| `CLAUDE.md` | **(b)** | Benchmark project instructions — rewrite for APPEB |
| `STATE.md` | **(b)** | Session state — moves to APPEB root |
| `pyproject.toml` | **(a)** | SWE-agent package config (name=sweagent). APPEB needs its own |
| `README.md` | **(a)** | SWE-agent README — APPEB needs its own |
| `LICENSE` | **(a)** | MIT license from SWE-agent |
| `CONTRIBUTING.md` | **(a)** | SWE-agent contributing guide |
| `SECURITY.md` | **(a)** | SWE-agent security policy |
| `SETUP_GUIDE.md` | **(d)** | May be our custom guide or upstream — check git blame |
| `mkdocs.yml` | **(a)** | SWE-agent docs config |
| `codecov.yml` | **(a)** | SWE-agent codecov config |
| `.pre-commit-config.yaml` | **(a)** | SWE-agent pre-commit hooks |
| `.git-blame-ignore-revs` | **(a)** | SWE-agent blame config |
| `.gitignore` | **(a+b)** | Mixed: upstream patterns + our custom entries (proxy apps, batch_results) |
| `mlc_config.json` | **(a)** | SWE-agent markdown link checker |
| `integrating_tools.pdf` | **(d)** | Possibly our documentation |
| `speedup_comparison_chart.py` | **(b)** | Our analysis script (hardcoded `/pscratch` paths) |
| `speedup_comparison_new.{png,pdf}` | **(b)** | Generated figures — move to `analysis/figures/` |
| `speedup_comparison.png` | **(b)** | Generated figure |
| `speedup_graph.png` | **(b)** | Generated figure |
| `output.out`, `output.txt` | **(b)** | Temp output files — should be .gitignored |
| `output_scheduled_claude*.log` | **(b)** | Scheduled run logs |
| `vllm_test.log` | **(b)** | vLLM testing log |
| `xyz.asc` | **(d)** | Unknown file |
| `v2.11.2.tar.gz` | **ignore** | hypre tarball — .gitignored |
| `hpc_ollama_*.yaml`, `hpc_podman_*.yaml` | **(d)** | Legacy HPC configs at root level — unclear if still used |
| `hypre`, `metis`, `metis-4.0` | **symlinks** | Dependency symlinks — .gitignored |

### 1.1 Modified Upstream SWE-agent Files

These SWE-agent core files were modified on the `dev` branch for HPC support (173 insertions, 30 deletions total). This is critical for the submodule decision — using the upstream repo would lose these patches:

| File | +/- | Modification |
|------|-----|-------------|
| `sweagent/tools/parsing.py` | +94/-2 | Multi-format function calling (`xml_function_calling` mode for Qwen) |
| `sweagent/agent/agents.py` | +37/-10 | Local profiling support; thinking block extraction |
| `sweagent/tools/tools.py` | +30/-6 | Profiling tools; blocklist validation |
| `sweagent/agent/models.py` | +22/-3 | Added Claude, Qwen model support; thinking blocks; parse modes |
| `sweagent/environment/swe_env.py` | +13/-1 | Profiling tool support |
| `sweagent/environment/repo.py` | +7/-2 | Sanitization; local repo support |

Only these 6 files differ between `main` and `dev`. The remaining `sweagent/` files (`run/`, `tools/commands.py`, etc.) are unmodified upstream code.

### Top-Level Directories

| Directory | Class | Notes |
|-----------|-------|-------|
| `sweagent/` | **(a)** | SWE-agent Python package (60+ files) — stays in submodule. **CAUTION**: Several core files have been modified for HPC support (see §1.1) |
| `tests/` | **(a)** | SWE-agent test suite |
| `docs/` | **(a)** | SWE-agent mkdocs documentation |
| `assets/` | **(a)** | SWE-agent branding images |
| `.github/` | **(a)** | SWE-agent CI/CD workflows |
| `.devcontainer/` | **(a)** | SWE-agent devcontainer config |
| `sweagent.egg-info/` | **(a)** | Generated package metadata |
| `build/` | **(a)** | Build artifacts |
| `batch/` | **(b)** | **Core benchmark infrastructure** — all custom |
| `batch_results/` | **(b)** | Benchmark output (SLURM logs, results) |
| `trajectories/` | **(b)** | Agent run trajectories + SWE-agent demos |
| `scripts/` | **(b)** | Custom scripts (setup_apps, reset_test_repos) |
| `analysis/` | **(b)** | Analysis scripts and figures |
| `dataset/` | **(b)** | Curated performance commits dataset |
| `baselines/` | **(b)** | Baseline outputs and timing data |
| `agent_docs/` | **(b)** | Our documentation (architecture, workflow) |
| `.planning/` | **(b)** | Session planning/handoff files |
| `.claude/` | **(b)** | Claude Code config (agents, commands, rules, skills, settings) |
| `.cursor/` | **(b)** | Cursor IDE rules |
| `config/` | **(a+c)** | Mixed: upstream SWE-agent configs + our `config/hpc/` |
| `tools/` | **(a+c)** | Mixed: upstream SWE-agent tool bundles + our harnesses/profiling |
| `Kripke/`, `Laghos/`, `Lulesh/`, `Quicksilver/` | **(b)** | Pristine app clones — move to `benchmarks/llnl-proxy-apps/` |
| `Kripke_test/`, `Laghos_test/`, `Lulesh_test/`, `Quicksilver_test/` | **(b)** | Working test copies — derived from pristine |
| `mfem/`, `hypre-2.11.2/`, `metis-4.0.3/` | **(b)** | Laghos dependencies — move to `benchmarks/llnl-proxy-apps/deps/` |
| `MACSio/` | **(d)** | Another proxy app — unclear if used |
| `ParEval-Repo/` | **(d)** | Parallel evaluation repo — unclear if used |
| `profiling_test_output/` | **(b)** | HPCToolkit test output — transient |
| `profiling_tools_basic/` | **(d)** | Python profiling tools (MCP?) — unclear if active |
| `.pytest_cache/` | **(a)** | Pytest cache |

### `batch/` Directory (all **(b)** benchmark infrastructure)

| File | Purpose |
|------|---------|
| `batch/hpc_benchmark_runner.py` | **Main orchestrator** — runs agents, validates results |
| `batch/run_benchmark.sh` | **Entrypoint shell script** — SBATCH wrapper, vLLM management |
| `batch/vllm_server.sh` | vLLM server startup/management |
| `batch/hpc_batch_runner.sh` | Legacy batch runner shell script |
| `batch/hpc_runner.py` | Legacy Python runner |
| `batch/run_full_matrix.sh` | Full matrix run script |
| `batch/report_generator.py` | Report generation |
| `batch/test_validation.py` | Validation test utilities |
| `batch/config/batch_defaults.yaml` | Default benchmark config |
| `batch/frameworks/base.py` | Framework launcher base class |
| `batch/frameworks/sweagent.py` | SWE-agent launcher |
| `batch/frameworks/claude.py` | Claude Code launcher |
| `batch/frameworks/codex.py` | Codex CLI launcher |
| `batch/frameworks/opencode.py` | OpenCode launcher |
| `batch/frameworks/openhands.py` | OpenHands launcher |
| `batch/frameworks/openhands_runner.py` | OpenHands subprocess runner |
| `batch/frameworks/prompt.py` | **Shared prompt templates** — used by all frameworks |
| `batch/__init__.py` | Package init |
| `batch/frameworks/__init__.py` | Package init |

### `tools/` Directory — Classification

| Tool Bundle | Class | Notes |
|-------------|-------|-------|
| `tools/kripke_harness/` | **(c)** | Our custom — Kripke build/run/timing |
| `tools/laghos_harness/` | **(c)** | Our custom — Laghos build/run/timing |
| `tools/lulesh_harness/` | **(c)** | Our custom — Lulesh build/run/timing |
| `tools/quicksilver_harness/` | **(c)** | Our custom — QS build/run/timing |
| `tools/gpa_harness/` | **(c)** | Our custom — GPA-Benchmark test tool |
| `tools/hpctoolkit/` | **(c)** | Our custom — HPCToolkit profiling wrapper |
| `tools/hatchet/` | **(c)** | Our custom — Hatchet analysis wrapper |
| `tools/nsight_compute/` | **(c)** | Our custom — Nsight Compute profiling |
| `tools/nsight_systems/` | **(c)** | Our custom — Nsight Systems profiling |
| `tools/profiling/` | **(c)** | Our custom — Generic profiling tools |
| `tools/system_info/` | **(c)** | Our custom — System info queries |
| `tools/image_tools/` | **(c)** | Our custom — Image viewing |
| `tools/forfeit/` | **(c)** | Our custom — Agent forfeit/exit tool |
| `tools/edit_anthropic/` | **(a+c)** | **CRITICAL SHARED** — used by SWE-agent AND all frameworks |
| `tools/windowed/` | **(a)** | SWE-agent core — file viewing |
| `tools/windowed_edit_linting/` | **(a)** | SWE-agent core — edit with linting |
| `tools/windowed_edit_replace/` | **(a)** | SWE-agent core — find/replace edit |
| `tools/windowed_edit_rewrite/` | **(a)** | SWE-agent core — rewrite edit |
| `tools/search/` | **(a)** | SWE-agent core — file search |
| `tools/submit/` | **(a)** | SWE-agent core — submission |
| `tools/review_on_submit_m/` | **(a+c)** | SWE-agent core — used in our configs |
| `tools/registry/` | **(a)** | SWE-agent core — env registry |
| `tools/filemap/` | **(a)** | SWE-agent core — file mapping |
| `tools/diff_state/` | **(a)** | SWE-agent core — state diffing |
| `tools/multilingual_setup/` | **(a)** | SWE-agent core — lang setup |
| `tools/web_browser/` | **(a)** | SWE-agent core — browser tools |
| `tools/PROFILING_TOOLS_SUMMARY.md` | **(c)** | Our documentation |
| `tools/HPCTOOLKIT_VERIFICATION.md` | **(c)** | Our documentation |
| `tools/IMPLEMENTATION_COMPLETE.md` | **(c)** | Our documentation |

### `config/` Directory — Classification

| Path | Class | Notes |
|------|-------|-------|
| `config/hpc/llnl_base.yaml` | **(c)** | Our template — SWE-agent config for LLNL apps |
| `config/hpc/{app}_{no,with}_profiling.yaml` | **(c)** | Our per-app configs (11 files) |
| `config/default.yaml` | **(a)** | SWE-agent default config |
| `config/default_*.yaml` | **(a)** | SWE-agent variants |
| `config/bash_only.yaml` | **(a)** | SWE-agent bash-only config |
| `config/coding_challenge.yaml` | **(a)** | SWE-agent coding challenge |
| `config/code-translation*.yaml` | **(a)** | SWE-agent translation configs |
| `config/demo/` | **(a)** | SWE-agent demo configs |
| `config/exotic/` | **(a)** | SWE-agent exotic configs |
| `config/human/` | **(a)** | SWE-agent human configs |
| `config/sweagent_0_7/` | **(a)** | SWE-agent 0.7 configs |
| `config/benchmarks/` | **(a)** | SWE-agent benchmark configs |
| `config/gpt4o_mini*.yaml` | **(d)** | Possibly our custom configs |
| `config/gpt-oss-120b-perlmutter.yaml` | **(b)** | Our custom config |
| `config/gptoss_local.yaml` | **(b)** | Our custom config |

### `trajectories/` — Classification

| Subdirectory | Class | Notes |
|--------------|-------|-------|
| `trajectories/demonstrations/` | **(a)** | SWE-agent demo trajectories (explicitly un-.gitignored) |
| `trajectories/benchmark_*` | **(b)** | Our benchmark run outputs |
| `trajectories/{sweagent,claude,codex,opencode,openhands}_*` | **(b)** | Our framework run outputs |
| `trajectories/hpc/` | **(b)** | Early HPC experiment outputs |
| `trajectories/krydzy/` | **(b)** | Personal experiment outputs |
| `trajectories/interactive_*` | **(b)** | Interactive verification runs |
| `trajectories/speed_study/` | **(b)** | Speed study data |
| `trajectories/jpc/` | **(b)** | JPC experiment data |
| `trajectories/goal6_gpa_sweagent/` | **(b)** | GPA experiment data |

---

## 2. Path-Dependent References

### 2.1 Python Files — `batch/`

#### `batch/hpc_benchmark_runner.py`
| Line | Reference | Type |
|------|-----------|------|
| 11 | `batch/hpc_benchmark_runner.py` | Self-reference in usage doc |
| 35 | `Path(__file__).resolve().parent.parent` | Derives `_sweagent_root` |
| 40 | `Path("/pscratch/sd/k/krydzy/GPA-Benchmark")` | **HARDCODED absolute path** |
| 45 | `Path("/pscratch/sd/k/krydzy/swefficiency")` | **HARDCODED absolute path** |
| 109 | `"dataset/curated_perf_commits.json"` | Relative path from SWEAGENT_ROOT |
| 144 | `"config/hpc/kripke_{profiling}.yaml"` | Relative config template path |
| 150 | `"config/hpc/laghos_{profiling}.yaml"` | Relative config template path |
| 156 | `"config/hpc/lulesh_{profiling}.yaml"` | Relative config template path |
| 162 | `"config/hpc/quicksilver_{profiling}.yaml"` | Relative config template path |
| 192 | `Path(__file__).parent.parent` | Derives `self.sweagent_root` |
| 211 | `self.sweagent_root / tmpl["pristine_subdir"]` | Pristine app paths |
| 212 | `self.sweagent_root / tmpl["test_subdir"]` | Test app paths |
| 246+ | `self.sweagent_root / dep` for mfem/hypre/metis | Dependency symlinks |
| 883 | `GPA_BENCHMARK_ROOT / "driver_apps.yaml"` | GPA config path |

#### `batch/frameworks/base.py`
| Line | Reference | Type |
|------|-----------|------|
| 120-126 | `HARNESS_MAP` — maps app name → `{app}_harness` | Tool dir names |
| 129-136 | `PROFILING_TOOL_DIRS` — `tools/hpctoolkit/bin`, etc. | Tool bin paths |
| 245 | `self.sweagent_root / "tools" / harness_name / "bin"` | Harness path construction |
| 264 | `self.sweagent_root / tool_dir` | Profiling tool path |
| 278 | `self.sweagent_root` via SWE_AGENT_ROOT export | Env var export |
| 279 | `"/pscratch/sd/k/krydzy/GPA-Benchmark"` | **HARDCODED absolute path** |
| 280 | `"/pscratch/sd/k/krydzy/GPA-Benchmark"` in PYTHONPATH | **HARDCODED absolute path** |
| 349-354 | `"{home_dir}/spack/share/spack/setup-env.sh"` | Spack path |

#### `batch/frameworks/sweagent.py`
| Line | Reference | Type |
|------|-----------|------|
| 16 | `from batch.frameworks.base import ...` | Package import |
| 23-27 | `"tools/kripke_harness"`, etc. | Tool bundle paths |
| 31-36 | `"tools/hpctoolkit"`, etc. | Profiling bundle paths |
| 40-46 | `"tools/registry"`, `"tools/edit_anthropic"`, etc. | Common bundle paths |
| 32 | `trajectories/demonstrations/str_replace_anthropic_demo.yaml` | Demo trajectory |

#### `batch/frameworks/openhands.py`
| Line | Reference | Type |
|------|-----------|------|
| 74 | `os.path.join(os.environ.get("HOME", ""), "envs", "sweagent")` | venv path |
| 95 | `f"{sweagent_root}/batch/frameworks/openhands_runner.py"` | Runner script path |
| 103 | `source "{sweagent_venv}/bin/activate"` | venv activation |
| 120 | `PYTHONPATH="{sweagent_root}:${{PYTHONPATH:-}}"` | PYTHONPATH manipulation |

#### `batch/frameworks/claude.py`
| Line | Reference | Type |
|------|-----------|------|
| 98 | `os.environ.get("HOME", str(Path.home()))` | Home dir for env setup |

#### `batch/frameworks/codex.py`
| Line | Reference | Type |
|------|-----------|------|
| 138 | `os.environ.get("HOME", str(Path.home()))` | Home dir for env setup |

#### `batch/frameworks/opencode.py`
| Line | Reference | Type |
|------|-----------|------|
| 98 | `os.environ.get("HOME", str(Path.home()))` | Home dir for env setup |

#### `batch/frameworks/prompt.py`
| Line | Reference | Type |
|------|-----------|------|
| (various) | Tool names like `kripke_build`, `kripke_run`, etc. | Tool command names (PATH-dependent) |

### 2.2 Shell Scripts

#### `batch/run_benchmark.sh`
| Line | Reference | Type |
|------|-----------|------|
| 11 | `#SBATCH -o /pscratch/sd/k/krydzy/SWE-agent/batch_results/benchmark_%j.out` | **HARDCODED absolute path** |
| 12 | `#SBATCH -e /pscratch/sd/k/krydzy/SWE-agent/batch_results/benchmark_%j.err` | **HARDCODED absolute path** |
| 49-51 | `SWEAGENT_ROOT` derivation from `BASH_SOURCE` | Script-relative path |
| 109 | `DATASET="${SWEAGENT_ROOT}/dataset/curated_perf_commits.json"` | Dataset path |
| 395-398 | `export SWEAGENT_ROOT` for sbatch spool | Root path propagation |
| 418 | `"${SWEAGENT_ROOT}/batch_results/..."` | Output dir |
| 419 | `"${SWEAGENT_ROOT}/trajectories/..."` | Trajectory dir |
| 598-607 | `"${SWEAGENT_ROOT}/Kripke_test/.git"` | Test repo git config |
| 721 | `cd "${SWEAGENT_ROOT}"` | CWD to root |
| 863 | `cd ${SWEAGENT_ROOT}` | CWD inside agent launch |
| 875 | `export SWEAGENT_ROOT='${SWEAGENT_ROOT}'` | Root propagation to agent |

#### `scripts/setup_apps.sh`
| Line | Reference | Type |
|------|-----------|------|
| 24-25 | `SWEAGENT_ROOT="$(dirname "$SCRIPT_DIR")"` | Script-relative root |
| (various) | Clones apps into `$SWEAGENT_ROOT/{App}/` and `{App}_test/` | App directory structure |

#### `scripts/reset_test_repos.sh`
| Line | Reference | Type |
|------|-----------|------|
| 18 | `SWEAGENT_ROOT="${SWEAGENT_ROOT:-/pscratch/sd/k/krydzy/SWE-agent}"` | **HARDCODED fallback** |
| (various) | References `$SWEAGENT_ROOT/Kripke_test`, etc. | Test repo paths |

#### `batch/vllm_server.sh`
| Line | Reference | Type |
|------|-----------|------|
| (various) | Uses `SWEAGENT_ROOT` and vLLM env vars | Root path |

### 2.3 YAML/Config Files

#### `config/hpc/llnl_base.yaml`
| Line | Reference | Type |
|------|-----------|------|
| 32 | `trajectories/demonstrations/str_replace_anthropic_demo.yaml` | Demo path |
| 35 | `api_base: "http://127.0.0.1:8008/v1"` | vLLM URL |
| 43 | `tools_base_path: /tmp/sweagent` | **CRITICAL**: SWE-agent copies tools here |
| 51 | `__APP_ROOT_VAR__: __APP_ROOT_PATH__` | Placeholder filled at runtime |
| 52-53 | `/tmp/sweagent/.swe-agent-env`, `/tmp/sweagent/state.json` | SWE-agent sandbox paths |
| 55 | `__BUNDLES__` | Placeholder — filled with `tools/...` paths |
| 82 | `path: __REPO_PATH__` | Workspace path placeholder |

#### `config/hpc/{app}_{profiling}.yaml` (11 files)
- All follow same pattern as `llnl_base.yaml`
- Reference tool bundle paths relative to repo root

#### `batch/config/batch_defaults.yaml`
| Line | Reference | Type |
|------|-----------|------|
| 19 | `default_output_dir: "batch_results"` | Output dir relative to root |
| 30 | `config_dir: "config/hpc"` | Config dir relative to root |
| 35-38 | `"Kripke_test"`, etc. | Test repo paths relative to root |

### 2.4 Tool Scripts (Harnesses)

All harness scripts (`tools/*_harness/bin/*`) use the same pattern:

| Pattern | Lines | Files |
|---------|-------|-------|
| `os.environ.get('{APP}_ROOT')` | ~line 20 | All `*_build`, `*_run` |
| `script_dir = os.path.dirname(os.path.abspath(__file__))` | ~line 22 | All `*_build` |
| `os.path.join(script_dir, '..', '..', '..', '{App}_test')` | ~line 23 | All `*_build` — **HARDCODED relative path** |
| `os.environ.get('SWE_AGENT_ROOT')` | various | `gpa_test`, some others |
| `"/pscratch/sd/k/krydzy/GPA-Benchmark"` | line 25 | `gpa_test` — **HARDCODED** |
| `_find_mpirun()` with fallback `/global/common/software/...` | various | All `*_run` — **Perlmutter-specific** |
| `_ensure_ld_library_path()` with Perlmutter lib dirs | various | All `*_run` |

### 2.5 Analysis Scripts

#### `analysis/plot_results.py`
| Line | Reference | Type |
|------|-----------|------|
| 28 | `Path(__file__).resolve().parent.parent / "batch_results"` | Results dir |
| 29 | `Path(__file__).resolve().parent / "figures"` | Output dir |

#### `speedup_comparison_chart.py` (root)
| Line | Reference | Type |
|------|-----------|------|
| 58-59 | `'/pscratch/sd/k/krydzy/SWE-agent/speedup_comparison_new.{png,pdf}'` | **HARDCODED absolute** |

### 2.6 Claude Code Files (`.claude/`)

#### `.claude/settings.local.json`
- No path references (only permission patterns and env vars)

#### `.claude/commands/load-state.md`
| Reference | Type |
|-----------|------|
| `STATE.md` | Root-relative file |
| `.planning/HANDOFF.md` | Root-relative dir |
| `batch_results/` | Root-relative dir |

#### `.claude/commands/save-state.md`
| Reference | Type |
|-----------|------|
| `STATE.md` | Root-relative file |
| `.planning/HANDOFF.md` | Root-relative dir |
| `.claude/skills/` | Root-relative dir |

#### `.claude/commands/write-plan.md`
| Reference | Type |
|-----------|------|
| `.planning/PLAN-current.md` | Root-relative file |

#### `.claude/rules/*.md`
| File | References |
|------|-----------|
| `harnesses.md` | `tools/*_harness/**` (glob pattern) |
| `pristine-repos.md` | `Kripke/**`, `Laghos/**`, `Lulesh/**`, `Quicksilver/**` |
| `test-repos.md` | `Kripke_test/**`, `Laghos_test/**`, etc. |
| `compute-nodes.md` | No specific paths |

#### `.claude/agents/*.md`
- `perlmutter-executor.md` — references compute node patterns
- `framework-expert.md` — references framework configs
- `profiling-expert.md` — references profiling tools
- `proxy-app-expert.md` — references proxy apps

#### `.claude/skills/*/SKILL.md` (17 skills)
- Each references specific tools, configs, and paths relevant to its domain
- Paths like `tools/kripke_harness/`, `config/hpc/`, `batch/frameworks/`

### 2.7 Cursor Rules (`.cursor/`)

#### `.cursor/rules/project-overview.mdc`
| Reference | Type |
|-----------|------|
| `sweagent/run` | Package path |
| `sweagent/agent/agents.py` | Source file |
| `sweagent/environment/swe_env.py` | Source file |
| `tools/` | Tool bundles dir |
| `inspector_cli.py` | Inspector script |
| `sweagent/inspector/server.py` | Inspector server |

---

## 3. Git-Specific Concerns

### 3.1 Remotes
```
origin    → parallelcodefoundry/SWE-agent.git  (our fork)
upstream  → SWE-agent/SWE-agent.git            (upstream SWE-agent)
personal  → KlaudiuszRydzy/swe-agent-testing.git
```

### 3.2 Branches
- `dev` — primary working branch (active)
- `main` — tracks upstream SWE-agent
- `benchmark-expansion`, `framework-integration`, `gptoss`, `local`, `fix-agent-execution` — local branches
- Upstream tracks many branches via `remotes/upstream/`

### 3.3 `.gitignore`
**Must split into two**:
- SWE-agent `.gitignore`: standard Python/SWE-agent patterns
- APPEB `.gitignore`: proxy apps, batch_results, trajectories, profiling output, dependency dirs

**Current custom entries that move to APPEB**:
```
Kripke/, Kripke_test/, Laghos/, Laghos_test/, Lulesh/, Lulesh_test/,
Quicksilver/, Quicksilver_test/, MACSio/, ParEval-Repo/,
mfem/, hypre-2.11.2/, hypre, metis-4.0.3/, metis, metis-4.0,
v2.11.2.tar.gz, batch_results/, profiling_test_output/
```

### 3.4 `.gitmodules`
**Does not exist yet** — no current submodules. Will need to be created for APPEB with:
- `frameworks/swe-agent` → `parallelcodefoundry/SWE-agent.git`
- `frameworks/opencode` → appropriate remote
- `frameworks/openhands` → appropriate remote
- `frameworks/codex-cli` → appropriate remote

### 3.5 CI/CD Workflows (`.github/workflows/`)
| File | References |
|------|-----------|
| `pytest.yaml` | `'.[dev]'` install, `trajectories/runner/` upload, `tests/` path, `docs/**` ignore |
| `build-docs.yaml` | SWE-agent docs build |
| `check-links-*.yaml` | SWE-agent link checking |

All CI/CD is SWE-agent specific. APPEB will need its own CI/CD (or none, since it runs on Perlmutter).

### 3.6 No Custom Git Hooks
No files in `.git/hooks/` beyond defaults. `.pre-commit-config.yaml` exists (SWE-agent upstream).

---

## 4. Claude Code Specific Files

### 4.1 In-Repo Files (`.claude/`)

| Path | Purpose | Path References |
|------|---------|-----------------|
| `.claude/settings.local.json` | Permissions, env vars | No path refs |
| `.claude/commands/load-state.md` | Session load slash command | `STATE.md`, `.planning/HANDOFF.md`, `batch_results/` |
| `.claude/commands/save-state.md` | Session save slash command | `STATE.md`, `.planning/HANDOFF.md`, `.claude/skills/` |
| `.claude/commands/write-plan.md` | Plan writing command | `.planning/PLAN-current.md` |
| `.claude/commands/check-experiment.md` | Experiment check command | `batch_results/` |
| `.claude/rules/compute-nodes.md` | Compute node rules | No specific paths |
| `.claude/rules/harnesses.md` | Harness rules | `tools/*_harness/**` |
| `.claude/rules/pristine-repos.md` | Read-only repos | `Kripke/**`, `Laghos/**`, etc. |
| `.claude/rules/test-repos.md` | Test repo rules | `Kripke_test/**`, etc. |
| `.claude/agents/framework-expert.md` | Framework agent | Framework-specific paths |
| `.claude/agents/perlmutter-executor.md` | Compute agent | Perlmutter-specific |
| `.claude/agents/profiling-expert.md` | Profiling agent | Profiling tool paths |
| `.claude/agents/proxy-app-expert.md` | Proxy app agent | Proxy app paths |
| `.claude/skills/` (17 skills) | Skill definitions | Various tool/config paths |

### 4.2 Project Root Files

| Path | Purpose | Migrates to APPEB? |
|------|---------|-------------------|
| `CLAUDE.md` | Main project instructions | Yes — **must rewrite** |
| `STATE.md` | Session state tracking | Yes |
| `.planning/HANDOFF.md` | Session handoff | Yes |
| `.planning/RESULTS-TRACKING-S46.md` | Results data | Yes |
| `.planning/PHASE2-GOALS.md` | Goals tracking | Yes |
| `.planning/PHASE2B-GOALS.md` | Goals tracking | Yes |
| `.planning/RALPH-*.md` | Ralph Wiggum automation | Yes |
| `.planning/session-prompts.md` | Session prompt templates | Yes |
| `.planning/OPTIMIZATION-INSIGHTS-S48.md` | Analysis | Yes |

### 4.3 Global Memory Files

Located at: `/global/homes/k/krydzy/.claude/projects/-pscratch-sd-k-krydzy-SWE-agent/memory/`

| File | Purpose |
|------|---------|
| `MEMORY.md` | Memory index (loaded every session) |
| `frameworks.md` | Framework-specific learnings |
| `proxy-apps.md` | Proxy app details |
| `perlmutter.md` | Perlmutter environment notes |

**Critical**: The memory directory path is derived from the project working directory path. Moving the repo to a new path (e.g., `/pscratch/sd/k/krydzy/APPEB`) will create a NEW memory directory. The old memory files must be manually migrated.

### 4.4 Skill Files That Reference Paths

All 17 skills in `.claude/skills/` reference paths. The most critical ones:

| Skill | Key Path References |
|-------|-------------------|
| `kripke/SKILL.md` | `tools/kripke_harness/`, `Kripke/`, `Kripke_test/`, build commands |
| `laghos/SKILL.md` | `tools/laghos_harness/`, `mfem/`, `hypre/`, `metis/` |
| `lulesh/SKILL.md` | `tools/lulesh_harness/`, `Lulesh/cuda/` |
| `quicksilver/SKILL.md` | `tools/quicksilver_harness/`, `Quicksilver/src/` |
| `gpa-benchmark/SKILL.md` | `tools/gpa_harness/`, GPA-Benchmark paths |
| `swe-agent-framework/SKILL.md` | `sweagent/`, `config/hpc/`, tool bundle paths |
| `perlmutter/SKILL.md` | NERSC-specific paths, module commands |
| `hpctoolkit/SKILL.md` | `tools/hpctoolkit/`, spack paths |
| `nsight-systems/SKILL.md` | `tools/nsight_systems/` |
| `nsight-compute/SKILL.md` | `tools/nsight_compute/` |

---

## 5. Circular Dependencies & Shared Modules

### 5.1 Critical Shared Components

#### `tools/edit_anthropic/` — **HIGHEST RISK**
- Used by SWE-agent's config system (`config/hpc/llnl_base.yaml` lists it as a bundle)
- Used by ALL frameworks indirectly (agents use `str_replace_editor` tool)
- Tab/space fix (commit `97e6f604`) applies to SWE-agent runs AND other frameworks
- **Decision needed**: Keep in APPEB `tools/` and point SWE-agent config at it, OR fork into SWE-agent submodule

#### `tools/review_on_submit_m/` — Medium Risk
- SWE-agent tool bundle used in our configs
- References workspace diff in its submit review message

#### `tools/registry/` — Medium Risk
- SWE-agent core tool, used in our configs
- Manages env vars within SWE-agent sandbox

#### `trajectories/demonstrations/` — Medium Risk
- SWE-agent demo trajectories (`.gitignore` has `!trajectories/demonstrations/**`)
- Referenced by `config/hpc/llnl_base.yaml` line 32
- These are SWE-agent upstream files but our configs reference them

### 5.2 Import Dependencies (Benchmark → SWE-agent)

| Benchmark File | SWE-agent Import | Purpose |
|---------------|-----------------|---------|
| `batch/frameworks/sweagent.py` | `from batch.frameworks.base import ...` | Own package (no SWE-agent import) |
| `batch/hpc_benchmark_runner.py` | `from batch.frameworks import ...` | Own package (no SWE-agent import) |
| **None** | `import sweagent` or `from sweagent import ...` | **NO direct Python imports of sweagent package** |

**Key finding**: The benchmark code does NOT import the `sweagent` Python package directly. It only:
1. Invokes `sweagent run` as a subprocess (via shell command in `sweagent.py`)
2. References SWE-agent tool bundles by path (in YAML configs)
3. References SWE-agent config format (YAML templates)

**Tool import caveat**: Some upstream SWE-agent tool bundles (`windowed/`, `windowed_edit_*`) import `from sweagent import TOOLS_DIR`. Our custom tools (all `*_harness/`, `hpctoolkit/`, `hatchet/`, `nsight_*`, `profiling/`, `system_info/`, `edit_anthropic/`, `forfeit/`, `gpa_harness/`) do NOT import from `sweagent`. This means our custom tools can be cleanly extracted without requiring the `sweagent` package.

### 5.3 Reverse Dependencies (SWE-agent → Benchmark)

| SWE-agent File | Benchmark Reference | Type |
|---------------|---------------------|------|
| **None** | N/A | **SWE-agent core has NO references to benchmark code** |

**Key finding**: This is a clean one-directional dependency. SWE-agent doesn't know about the benchmark. The benchmark references SWE-agent only through:
1. CLI invocation (`sweagent run --config ...`)
2. YAML config file format
3. Tool bundle directory conventions

### 5.4 Interface Points

The interfaces between APPEB and SWE-agent are:

1. **CLI**: `sweagent run --config <yaml> --repo.path <path>` — subprocess call
2. **YAML configs**: Must follow SWE-agent's config schema (`agent:`, `env:`, `tools:`)
3. **Tool bundles**: Directories with `config.yaml` + `bin/` + optional `install.sh` — must be accessible by path
4. **Tool base path**: SWE-agent copies tools to `/tmp/sweagent/` — our tools must work from there
5. **Trajectory output**: SWE-agent writes to trajectory dirs — benchmark reads them back
6. **`tools_base_path`**: In YAML config, tells SWE-agent where tool bundles live

### 5.5 Env Var Contract

The benchmark and SWE-agent share these env vars:

| Variable | Set By | Used By |
|----------|--------|---------|
| `SWEAGENT_ROOT` / `SWE_AGENT_ROOT` | Benchmark shell scripts | Tool harnesses (for finding pristine repos) |
| `{APP}_ROOT` | Framework launchers | Harness scripts |
| `OPENAI_API_BASE` | Benchmark runner | SWE-agent/LiteLLM |
| `OPENAI_API_KEY` | Benchmark runner | SWE-agent/LiteLLM |
| `CUDA_VISIBLE_DEVICES` | Framework launchers | Harness MPI scripts |
| `OMP_NUM_THREADS` | Framework launchers | App runtime |
| `PYTHONUNBUFFERED` | Framework launchers | Python subprocesses |
| `GPA_BENCHMARK_ROOT` | Framework launchers | GPA harness |

---

## 6. Summary of Hardcoded Absolute Paths

These are the paths that **MUST** be updated during migration.

### 6.1 Core Infrastructure (highest priority)

| Path | Files | Occurrences |
|------|-------|-------------|
| `/pscratch/sd/k/krydzy/SWE-agent` | `run_benchmark.sh:11-12`, `hpc_batch_runner.sh:11-12`, `run_full_matrix.sh:20,51`, `reset_test_repos.sh:18`, `test_validation.py:16` | 8 |
| `/pscratch/sd/k/krydzy/GPA-Benchmark` | `hpc_benchmark_runner.py:40`, `base.py:279-280`, `gpa_test:25` | 4 |
| `/pscratch/sd/k/krydzy/swefficiency` | `hpc_benchmark_runner.py:45` | 1 |
| `/global/common/software/.../openmpi/5.0.7/bin/mpirun` | `kripke_run:23`, `laghos_run:31`, `lulesh_run:27`, `qs_run:28` | 4 |

### 6.2 Per-App SWE-agent Configs (legacy but still referenced)

All 8 per-app config YAMLs (`config/hpc/{app}_{with,no}_profiling.yaml`) contain hardcoded paths:

| Pattern | Occurrences |
|---------|-------------|
| `{APP}_ROOT: /pscratch/.../SWE-agent/{App}_test` | 8 files × 1 = 8 |
| `path: /pscratch/.../SWE-agent/{App}_test` | 8 files × 1 = 8 |

**Note**: The base template `llnl_base.yaml` uses placeholders (`__APP_ROOT_PATH__`, `__REPO_PATH__`) that are filled at runtime — these per-app configs are legacy but may still be used for standalone SWE-agent runs.

### 6.3 SWE-agent Demo Trajectory

| Path | Files | Occurrences |
|------|-------|-------------|
| `trajectories/demonstrations/str_replace_anthropic_demo.yaml` | All 11 `config/hpc/*.yaml` files | 11 |

This is a relative path that currently resolves from the repo root. After restructure, it would need to point to `frameworks/swe-agent/trajectories/demonstrations/...` or be copied locally.

### 6.4 Dataset & Characterization Scripts

| Path | Files | Occurrences |
|------|-------|-------------|
| `/pscratch/.../SWE-agent/{Kripke,Laghos,Lulesh,Quicksilver}` | `scrape_performance_commits.py:97-112`, `verify_builds.py:37-48` | 8 |
| `/pscratch/.../SWE-agent/Laghos/laghos` | `char_laghos*.sbatch` (4 files), `characterize_laghos*.sh` (2 files) | 6 |
| `/pscratch/.../SWE-agent/batch_results/laghos_characterization/` | Same 6 characterization scripts | 6 |
| `/pscratch/.../SWE-agent/dataset/curated_perf_commits.json` | `audit_commits.py:22` | 1 |

### 6.5 Claude Code Files (`.claude/`)

| Scope | Files | Occurrences |
|-------|-------|-------------|
| `/pscratch/sd/k/krydzy/...` paths in skill files | 16 skills + 2 agents | **49 total** |

Most are in SKILL.md files for kripke, laghos, lulesh, quicksilver, gpa-benchmark, codex-cli, openhands, opencode, hatchet, swefficiency, and in `perlmutter-executor.md`.

### 6.6 Other Root-Level & Misc

| Path | Files | Occurrences |
|------|-------|-------------|
| `speedup_comparison_new.{png,pdf}` | `speedup_comparison_chart.py:58-59` | 2 |
| `/pscratch/.../algorithms/` | `gpt4o_mini_algorithms.yaml`, `hpc_podman_algorithms_isolated.yaml` | 3 |
| `/pscratch/.../test-repo` | `hpc_ollama_*.yaml` (2 files) | 2 |
| `/pscratch/.../hpctoolkit` | `tools/HPCTOOLKIT_VERIFICATION.md`, `tools/IMPLEMENTATION_COMPLETE.md` | 7+ (docs) |
| `/pscratch/.../hatchet` | `tools/PROFILING_TOOLS_SUMMARY.md`, `tools/IMPLEMENTATION_COMPLETE.md` | 10+ (docs) |

### 6.7 Env-Var-Based Paths

| Env Var | Default | Files |
|---------|---------|-------|
| `~/envs/sweagent` (SWEAGENT_VENV) | `openhands.py:74`, `sweagent.py:151`, `run_benchmark.sh:107` | 3 |
| `~/hatchet` (HATCHET_DIR) | `run_benchmark.sh:108,726-729,868` | 3 |
| `$PSCRATCH/hf-cache` (HF_HOME) | `run_benchmark.sh:580` | 1 |
| `~/spack/share/spack/setup-env.sh` | `base.py:350` | 1 |
| `/tmp/sweagent` (SWE-agent sandbox) | `llnl_base.yaml:43,52-53` | 1 (SWE-agent convention, don't change) |

### 6.8 Relative Path Dependencies in Harness Tools

All harness `*_build` and `*_run` scripts use `os.path.join(script_dir, '..', '..', '..', '{App}_test')` as fallback path resolution (13 occurrences across 8 harness scripts). These assume the tool lives at `tools/{app}_harness/bin/` relative to the repo root where `{App}_test/` also lives.

---

## 7. Risk Matrix

| Risk | Severity | Impact | Mitigation |
|------|----------|--------|------------|
| SWE-agent tool bundle paths break | **HIGH** | All SWE-agent runs fail | Use `tools_base_path` config to point at APPEB `tools/` |
| `SWEAGENT_ROOT` env var semantics change | **HIGH** | All harnesses fail to find apps | Rename to `APPEB_ROOT` or `BENCHMARK_ROOT` |
| Claude Code memory lost | **MEDIUM** | 50 sessions of learnings gone | Manually migrate memory dir |
| Trajectory path structure changes | **MEDIUM** | Result analysis breaks | Keep `batch_results/` structure |
| GPA-Benchmark hard paths break | **MEDIUM** | GPA tests fail | Make `GPA_BENCHMARK_ROOT` relative or configurable |
| `.gitignore` incomplete | **LOW** | Large files accidentally committed | Careful `.gitignore` construction |
| CI/CD doesn't apply | **LOW** | No automated testing | APPEB runs on Perlmutter, not GitHub CI |
