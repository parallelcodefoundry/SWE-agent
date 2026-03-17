# APPEB Migration Checklist

Ordered by dependency — things that must happen first are listed first.
Each task is atomic and can be verified independently.

---

## Phase 0: Pre-Migration (Before Any File Moves)

### 0.1 Preparation
- [ ] **Save current state**: Run `/save-state` to capture session 50+ state
- [ ] **Commit all work**: Ensure `dev` branch is clean — `git status` shows nothing uncommitted
- [ ] **Tag the fork**: `git tag pre-appeb-migration` on current HEAD for rollback
- [ ] **Export memory files**: Copy `/global/homes/k/krydzy/.claude/projects/-pscratch-sd-k-krydzy-SWE-agent/memory/` to a backup location
- [ ] **Document current results**: Ensure `batch_results/` and `trajectories/` are backed up or can be regenerated

### 0.2 Create New Repository
- [ ] **Create APPEB repo on GitHub** under `parallelcodefoundry` org (or personal)
- [ ] **Clone to scratch space**: `cd /pscratch/sd/k/krydzy && git clone <url> APPEB` (physical location on Lustre)
- [ ] **Create symlink from home**: `ln -s /pscratch/sd/k/krydzy/APPEB /global/homes/k/krydzy/APPEB` (convenience symlink, same pattern as current SWE-agent)
- [ ] **Initialize basic structure**: Create empty dirs matching target layout:
  ```
  mkdir -p benchmarks/llnl-proxy-apps-and-dependencies
  mkdir -p benchmarks/gpa-benchmark
  mkdir -p frameworks
  mkdir -p batch/frameworks batch/config
  mkdir -p batch_results
  mkdir -p tools
  mkdir -p scripts
  mkdir -p analysis/figures
  mkdir -p agent_docs
  mkdir -p dataset
  mkdir -p baselines
  mkdir -p .planning
  mkdir -p .claude/commands .claude/rules .claude/agents .claude/skills
  mkdir -p .cursor/rules
  ```

---

## Phase 1: Framework Submodules (No Path Dependencies)

### 1.1 SWE-agent Submodule
- [ ] **Decide**: Use `parallelcodefoundry/SWE-agent` fork or upstream `SWE-agent/SWE-agent`?
  - Fork preserves our tool modifications on `dev` branch
  - Upstream is cleaner but loses custom tool patches
  - **Recommendation**: Fork. Keep `dev` branch with our patches, periodically merge upstream `main`
- [ ] **Add submodule**: `git submodule add -b dev https://github.com/parallelcodefoundry/SWE-agent.git frameworks/swe-agent`
- [ ] **Verify**: `ls frameworks/swe-agent/sweagent/` shows Python package

### 1.2 Other Framework Submodules
- [ ] **Add OpenCode**: `git submodule add <opencode-url> frameworks/opencode`
- [ ] **Add OpenHands**: `git submodule add <openhands-url> frameworks/openhands`
- [ ] **Add Codex CLI**: `git submodule add <codex-url> frameworks/codex-cli`
- [ ] **Decision needed**: Are these our forks or upstream repos? (Currently they're installed via pip/bun, not as submodules)

---

## Phase 2: Move Framework-Agnostic Tools (Critical Path)

### 2.1 Custom Tool Bundles → `tools/`
These tools are currently in the SWE-agent fork. They need to be in APPEB's `tools/` dir.

- [ ] **Copy custom harnesses**:
  - `tools/kripke_harness/` → `tools/kripke_harness/`
  - `tools/laghos_harness/` → `tools/laghos_harness/`
  - `tools/lulesh_harness/` → `tools/lulesh_harness/`
  - `tools/quicksilver_harness/` → `tools/quicksilver_harness/`
  - `tools/gpa_harness/` → `tools/gpa_harness/`
- [ ] **Copy custom profiling tools**:
  - `tools/hpctoolkit/` → `tools/hpctoolkit/`
  - `tools/hatchet/` → `tools/hatchet/`
  - `tools/nsight_compute/` → `tools/nsight_compute/`
  - `tools/nsight_systems/` → `tools/nsight_systems/`
  - `tools/profiling/` → `tools/profiling/`
  - `tools/system_info/` → `tools/system_info/`
  - `tools/image_tools/` → `tools/image_tools/`
- [ ] **Copy shared SWE-agent tools needed by configs**:
  - `tools/edit_anthropic/` → `tools/edit_anthropic/` (CRITICAL — used by all frameworks)
  - `tools/review_on_submit_m/` → `tools/review_on_submit_m/`
  - `tools/registry/` → `tools/registry/`
  - `tools/forfeit/` → `tools/forfeit/`
  - `tools/filemap/` → `tools/filemap/`
- [ ] **Verify**: All `config.yaml` files in each tool bundle reference correct relative paths
- [ ] **Set permissions**: `chmod 755 tools/*/bin/*` on all harness executables

### 2.2 Decision: `edit_anthropic` Location
- [ ] **Option A** (recommended): Keep a copy in APPEB `tools/`, AND keep the original in the SWE-agent fork
  - Pro: SWE-agent submodule is self-contained; APPEB tools work independently
  - Con: Duplicate maintenance
- [ ] **Option B**: Only in APPEB, SWE-agent config `tools_base_path` points to APPEB `tools/`
  - Pro: Single source of truth
  - Con: SWE-agent can't run standalone
- [ ] **Document decision**

---

## Phase 3: Move Benchmark Infrastructure

### 3.1 Core Batch Framework → `batch/`
- [ ] **Copy all batch files**:
  - `batch/hpc_benchmark_runner.py`
  - `batch/run_benchmark.sh`
  - `batch/vllm_server.sh`
  - `batch/hpc_batch_runner.sh`
  - `batch/hpc_runner.py`
  - `batch/run_full_matrix.sh`
  - `batch/report_generator.py`
  - `batch/test_validation.py`
  - `batch/__init__.py`
  - `batch/config/batch_defaults.yaml`
  - `batch/frameworks/` (entire directory)

### 3.2 Update `SWEAGENT_ROOT` → `APPEB_ROOT` (or `BENCHMARK_ROOT`)
This is the most impactful rename. Every reference to the project root must be updated.

- [ ] **Choose new variable name**: `APPEB_ROOT` or `BENCHMARK_ROOT`?
- [ ] **Update `batch/run_benchmark.sh`**:
  - Line 11-12: Change SBATCH output paths to use new root
  - Line 49-51: Change `SWEAGENT_ROOT` variable name
  - Line 109: Dataset path
  - Line 395-398: Export new variable name
  - Line 418-419: Output/trajectory dirs
  - Line 598-607: Kripke_test git config paths
  - Line 721, 863, 875: cd and export commands
- [ ] **Update `batch/hpc_benchmark_runner.py`**:
  - Line 35-37: `_sweagent_root` → `_appeb_root`
  - Line 192: `self.sweagent_root` → `self.appeb_root`
  - All `sweagent_root` references throughout
- [ ] **Update `batch/frameworks/base.py`**:
  - Line 171-177: `sweagent_root` parameter → `appeb_root`
  - Line 245: Harness path construction
  - Line 264: Profiling tool path
  - Line 278: `SWE_AGENT_ROOT` env var export
- [ ] **Update all framework launchers**: `sweagent.py`, `claude.py`, `codex.py`, `opencode.py`, `openhands.py`
- [ ] **Update `scripts/setup_apps.sh`**: Line 24-25 root derivation
- [ ] **Update `scripts/reset_test_repos.sh`**: Line 18 hardcoded fallback
- [ ] **Update tool harnesses**: All `SWE_AGENT_ROOT` env var references in `tools/*/bin/*`
- [ ] **Update YAML configs**: `SWE_AGENT_ROOT` references in `config/hpc/*.yaml`

### 3.3 Update Hardcoded Absolute Paths (Comprehensive — ~100+ occurrences)

**Batch infrastructure** (8 occurrences):
- [ ] `batch/run_benchmark.sh` lines 11-12 (SBATCH output paths)
- [ ] `batch/hpc_batch_runner.sh` lines 11-12 (SBATCH output paths)
- [ ] `batch/run_full_matrix.sh` lines 20, 51 (log path, cd)
- [ ] `batch/test_validation.py` line 16 (SWEAGENT_ROOT)
- [ ] `scripts/reset_test_repos.sh` line 18 (fallback root)

**GPA/SWE-fficiency paths** (5 occurrences) → make configurable via env var:
- [ ] `batch/hpc_benchmark_runner.py` lines 40, 45
- [ ] `batch/frameworks/base.py` lines 279-280
- [ ] `tools/gpa_harness/bin/gpa_test` line 25

**Per-app SWE-agent config YAMLs** (16 occurrences across 8 files):
- [ ] `config/hpc/{kripke,laghos,lulesh,quicksilver}_{with,no}_profiling.yaml` — each has `{APP}_ROOT` and `path:` hardcoded
- [ ] **Decision**: Are these legacy files still used? If benchmark runner generates configs from `llnl_base.yaml` templates, these may be dead code

**Demo trajectory path** (11 occurrences):
- [ ] `config/hpc/*.yaml` all reference `trajectories/demonstrations/str_replace_anthropic_demo.yaml`
- [ ] Must either copy demo file to APPEB or update path to `frameworks/swe-agent/trajectories/...`

**Dataset scripts** (9 occurrences):
- [ ] `dataset/scrape_performance_commits.py` lines 97-112 (4 app paths)
- [ ] `dataset/verify_builds.py` lines 37-48 (8 paths: 4 test + 4 pristine)
- [ ] `scripts/audit_commits.py` line 22 (dataset path)

**Characterization scripts** (12 occurrences across 6 files):
- [ ] `scripts/char_laghos*.sbatch` (4 files with SBATCH outputs + exe paths)
- [ ] `scripts/characterize_laghos*.sh` (2 files with exe + results paths)

**Claude Code files** (49 occurrences across 18 files):
- [ ] 16 skill files + 2 agent files with `/pscratch/...` paths (see §6.5 in audit)
- [ ] These can be bulk find-and-replaced

**Analysis/misc** (5 occurrences):
- [ ] `speedup_comparison_chart.py` lines 58-59
- [ ] Root-level HPC YAML configs: `hpc_ollama_*.yaml`, `hpc_podman_*.yaml`, `gpt4o_mini_algorithms.yaml`

**Documentation markdown** (17+ occurrences):
- [ ] `tools/PROFILING_TOOLS_SUMMARY.md`, `HPCTOOLKIT_VERIFICATION.md`, `IMPLEMENTATION_COMPLETE.md`

### 3.4 SWE-agent Config Files → `config/hpc/`
- [ ] **Copy HPC configs**:
  - `config/hpc/llnl_base.yaml`
  - `config/hpc/{app}_{no,with}_profiling.yaml` (10 files)
  - `config/hpc/gpa_{no,with}_profiling.yaml`
- [ ] **Update tool bundle paths in configs**: These currently reference `tools/kripke_harness` etc. — verify these resolve relative to the new repo root
- [ ] **Update `tools_base_path`** in `llnl_base.yaml` (line 43): Currently `/tmp/sweagent` — this is SWE-agent's sandbox path, should remain unchanged
- [ ] **Update demo trajectory path**: `llnl_base.yaml` line 32 references `trajectories/demonstrations/str_replace_anthropic_demo.yaml` — this is in the SWE-agent submodule. Path needs to be `frameworks/swe-agent/trajectories/demonstrations/...` or copied locally
- [ ] **Copy root-level HPC configs if still used**:
  - `config/gpt-oss-120b-perlmutter.yaml`
  - `config/gptoss_local.yaml`
  - `hpc_ollama_*.yaml`, `hpc_podman_*.yaml` (if still used, or delete)

---

## Phase 4: Move Benchmark Data & Results

### 4.1 Dataset
- [ ] **Copy dataset files**:
  - `dataset/curated_perf_commits.json`
  - `dataset/curated_perf_commits_old.json`
  - `dataset/curated_perf_commits_v2.json`
  - `dataset/hpc_perf_commits.json`
  - `dataset/verified_candidates.json`
  - `dataset/scrape_performance_commits.py`
  - `dataset/upload_to_huggingface.py`
  - `dataset/verify_builds.py`

### 4.2 Trajectories
- [ ] **Move benchmark trajectories to `batch_results/trajectories/`**:
  - All `trajectories/{framework}_*` dirs
  - All `trajectories/benchmark_*` dirs
  - `trajectories/hpc/`, `trajectories/speed_study/`, etc.
- [ ] **Handle SWE-agent demo trajectories**: `trajectories/demonstrations/` stays in SWE-agent submodule
- [ ] **Update trajectory references**:
  - `batch/run_benchmark.sh` line 419: trajectory dir construction
  - `config/hpc/llnl_base.yaml` line 32: demo path
  - Any analysis scripts that read trajectories

### 4.3 Baselines
- [ ] **Copy**: `baselines/kripke/`, `baselines/quicksilver/` → `baselines/`

### 4.4 Analysis
- [ ] **Copy**: `analysis/plot_results.py`, `analysis/figures/` → `analysis/`
- [ ] **Update path references** in `analysis/plot_results.py` (lines 28-29)

### 4.5 Batch Results
- [ ] **Copy existing results**: `batch_results/` → `batch_results/`
- [ ] **Update SBATCH output paths**: `run_benchmark.sh` lines 11-12

---

## Phase 5: Move Proxy Apps & Dependencies

### 5.1 App Structure Decision
- [ ] **Decision**: Where do pristine apps live?
  - **Option A**: `benchmarks/llnl-proxy-apps-and-dependencies/{App}/` (as target suggests)
  - **Option B**: Keep at top level (less path changes but messier)
  - **Note**: These are git-ignored anyway (cloned at setup time)
- [ ] **Decision**: Where do test copies live?
  - Same directory as pristine with `_test` suffix?
  - Separate `workspaces/` directory?

### 5.2 Update `scripts/setup_apps.sh`
- [ ] **Update clone paths**: Currently clones into `$SWEAGENT_ROOT/{App}/`
- [ ] **Update test copy paths**: Currently creates `{App}_test/`
- [ ] **Update dependency paths**: mfem, hypre, metis locations

### 5.3 Update `scripts/reset_test_repos.sh`
- [ ] **Update all test repo paths**
- [ ] **Update hardcoded fallback** (line 18)

### 5.4 Update Harness Path Resolution
All harness scripts (`tools/*_harness/bin/*_build`) use `os.path.join(script_dir, '..', '..', '..', '{App}_test')` as fallback.
- [ ] **Update relative paths** for new directory layout
- [ ] **Or**: Make all harnesses rely solely on `{APP}_ROOT` env var (recommended)

### 5.5 Update Laghos Dependency Symlinks
- [ ] `hpc_benchmark_runner.py` line 246+: symlinks `mfem/`, `hypre/`, `metis-4.0.3/` into workspace
- [ ] **Update source paths** for new dependency locations

---

## Phase 6: Claude Code Migration (Critical for Continuity)

### 6.1 Copy Claude Code Configuration
- [ ] **Copy `.claude/` directory** to APPEB root
- [ ] **Copy `CLAUDE.md`** — will need major rewrite (Phase 7)
- [ ] **Copy `STATE.md`** — update paths
- [ ] **Copy `.planning/`** — all handoff/planning files

### 6.2 Update Claude Code Path References
- [ ] **Update `.claude/rules/harnesses.md`**: `tools/*_harness/**` (should still work)
- [ ] **Update `.claude/rules/pristine-repos.md`**: Paths depend on Phase 5.1 decision
- [ ] **Update `.claude/rules/test-repos.md`**: Same
- [ ] **Update `.claude/commands/load-state.md`**: `batch_results/` reference
- [ ] **Update `.claude/commands/save-state.md`**: `.claude/skills/` reference
- [ ] **Update `.claude/commands/write-plan.md`**: `.planning/` reference
- [ ] **Update all 17 skill files**: Paths to tools, configs, apps
- [ ] **Update 4 agent files**: Framework, profiling, proxy app, Perlmutter references

### 6.3 Migrate Claude Code Memory
- [ ] **Copy memory files** from old project dir to new one:
  ```bash
  # Old: /global/homes/k/krydzy/.claude/projects/-pscratch-sd-k-krydzy-SWE-agent/memory/
  # New: /global/homes/k/krydzy/.claude/projects/-pscratch-sd-k-krydzy-APPEB/memory/
  ```
- [ ] **Verify**: Start a Claude Code session in APPEB dir, check memory loads
- [ ] **Update MEMORY.md**: Remove SWE-agent-specific entries, update paths

### 6.4 Copy Cursor Rules
- [ ] **Copy `.cursor/rules/`** to APPEB
- [ ] **Rewrite `project-overview.mdc`** for APPEB (currently describes SWE-agent internals)

---

## Phase 7: Rewrite Documentation

### 7.1 CLAUDE.md
- [ ] **Rewrite entirely** for APPEB project structure
- [ ] **Update all path references** (project structure section)
- [ ] **Update commands** (key commands section)
- [ ] **Update critical rules** (proxy app locations, build modes, etc.)
- [ ] **Remove SWE-agent-specific content** (upstream tracking, etc.)

### 7.2 Agent Docs
- [ ] **Update `agent_docs/architecture.md`** for new structure
- [ ] **Update `agent_docs/experiment-workflow.md`** for new paths
- [ ] **Update `agent_docs/results-analysis.md`** if path-dependent
- [ ] **Update `agent_docs/usage-guide.md`** for new commands

### 7.3 New README
- [ ] **Write APPEB README.md** (distinct from SWE-agent README)

---

## Phase 8: .gitignore & Package Config

### 8.1 APPEB .gitignore
- [ ] **Create `.gitignore`** with:
  ```
  # Proxy apps (cloned at setup time)
  benchmarks/llnl-proxy-apps-and-dependencies/Kripke/
  benchmarks/llnl-proxy-apps-and-dependencies/Laghos/
  # ... etc for all apps, test copies, and deps

  # Results & trajectories (large, regenerated)
  batch_results/

  # Python
  __pycache__/
  *.py[cod]
  *.egg-info/

  # Environment
  *.env
  .venv/

  # Editor
  .idea/
  .vscode/
  ```
- [ ] **Un-ignore SWE-agent demo trajectories** if still needed:
  `!frameworks/swe-agent/trajectories/demonstrations/**`

### 8.2 Package Configuration
- [ ] **Create APPEB `pyproject.toml`** (separate from SWE-agent's):
  - Package name: `appeb` or `hpc-agent-benchmark`
  - Dependencies: only benchmark-specific (not SWE-agent deps)
  - No `[project.scripts]` entry for `sweagent` (that stays in the submodule)
- [ ] **Or**: No pyproject.toml if APPEB isn't installable as a package

---

## Phase 9: Validation & Testing

### 9.1 Smoke Tests (Login Node)
- [ ] **Verify imports**: `cd /pscratch/sd/k/krydzy/APPEB && python3 -c "from batch.frameworks.base import FrameworkLauncher"`
- [ ] **Verify SWE-agent submodule**: `python3 -c "import sweagent"` (may need `pip install -e frameworks/swe-agent`)
- [ ] **Verify tool permissions**: All `tools/*/bin/*` are executable
- [ ] **Verify config loading**: `python3 -c "import yaml; yaml.safe_load(open('config/hpc/llnl_base.yaml'))"`
- [ ] **Verify `setup_apps.sh`** runs (clone only, no build): `./scripts/setup_apps.sh --no-build`
- [ ] **Verify `reset_test_repos.sh`** runs

### 9.2 Integration Tests (Compute Node)
- [ ] **Allocate node**: `salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m5083`
- [ ] **Build one app**: `./scripts/setup_apps.sh --kripke`
- [ ] **Run harness directly**: Test `kripke_build` and `kripke_run` from new tool paths
- [ ] **Run benchmark**: `bash batch/run_benchmark.sh --base --kripke --framework claude --skip-vllm`
- [ ] **Verify results**: Check `batch_results/` for output

### 9.3 Claude Code Validation
- [ ] **Start session in APPEB dir**: Verify CLAUDE.md loads
- [ ] **Run `/load-state`**: Verify STATE.md and HANDOFF.md accessible
- [ ] **Check memory**: Verify memory files migrated correctly
- [ ] **Check skills**: Run a skill command and verify it works
- [ ] **Run `/save-state`**: Verify state saves to new location

---

## Phase 10: Cleanup & Finalization

### 10.1 Remove Benchmark Files from SWE-agent Fork
- [ ] **Decision**: Remove our custom files from the fork, or just leave them?
  - If removing: branch `dev` loses benchmark code
  - If keeping: fork stays as-is, APPEB is the canonical location
  - **Recommendation**: Keep fork as-is for now, deprecate later

### 10.2 Update External References
- [ ] **Update `~/.openai_env`** if it references old paths
- [ ] **Update any cron jobs** or scheduled scripts
- [ ] **Update any `nohup` commands** that reference old paths

### 10.3 Final Commit
- [ ] **Stage and commit** all APPEB files
- [ ] **Tag**: `git tag v0.1.0-initial-migration`
- [ ] **Push** to remote

---

## Key Decisions Required (Before Starting)

| # | Decision | Options | Impact |
|---|----------|---------|--------|
| 1 | **New variable name** for project root | `APPEB_ROOT`, `BENCHMARK_ROOT`, `HPC_BENCH_ROOT` | All scripts, all env vars |
| 2 | **SWE-agent submodule**: fork or upstream? | Fork (preserves patches) vs Upstream (cleaner) | Tool compatibility |
| 3 | **Other framework submodules**: forks or upstream? | Currently pip-installed, not cloned | Installation process |
| 4 | **Proxy app locations** | `benchmarks/llnl-proxy-apps/` vs top-level | Many path references |
| 5 | **`edit_anthropic` duplication** | Copy to APPEB, or share from submodule | Tool maintenance |
| 6 | **Trajectory location** | `batch_results/trajectories/` vs `trajectories/` | SWE-agent expects `trajectories/` |
| 7 | **GPA-Benchmark**: submodule or external? | Currently separate repo at `/pscratch/.../GPA-Benchmark` | Path references |
| 8 | **`pyproject.toml`**: installable package? | Yes (for imports) vs No (just scripts) | Import mechanism |
| 9 | **Keep old fork intact?** | Preserve vs strip benchmark code | Rollback safety |

---

## Estimated Effort by Phase

| Phase | Tasks | Dependencies | Effort |
|-------|-------|-------------|--------|
| 0 | 5 | None | Small — backup/prep |
| 1 | 6 | Phase 0 | Small — git submodule add |
| 2 | 7 | Phase 1 (for submodule reference) | Medium — file copies + decision |
| 3 | 15 | Phase 2 (tools must be in place) | **Large** — most path updates |
| 4 | 8 | Phase 3 (batch code must work) | Medium — data movement |
| 5 | 6 | Phase 3 (scripts must be updated) | Medium — app path updates |
| 6 | 8 | Phase 3 (core paths established) | Medium — Claude Code continuity |
| 7 | 5 | All above | Medium — documentation |
| 8 | 3 | Phase 7 | Small — config files |
| 9 | 8 | All above | Medium — validation |
| 10 | 4 | Phase 9 (tests pass) | Small — cleanup |

**Critical path**: Phase 0 → 1 → 2 → 3 (path updates) → 9 (validation). Everything else can be parallelized around Phase 3.
