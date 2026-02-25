#!/usr/bin/env python3
"""Standalone OpenHands SDK runner for headless benchmark execution.

Called by the OpenHands launcher's build_launch_command() shell script.
Uses the OpenHands SDK (LocalConversation + Agent) since the openhands
CLI is a TUI without headless mode.

Usage:
    python3 batch/frameworks/openhands_runner.py \
        --model gpt-4o-mini \
        --workspace /path/to/workspace \
        --prompt-file /path/to/prompt.txt \
        --trajectory-file /path/to/output.jsonl \
        --max-iterations 50
"""

import argparse
import json
import os
import sys


# Prevent batch/frameworks/openhands.py from shadowing the pip openhands package.
# When run directly, Python adds the script's parent directory (batch/frameworks/)
# to sys.path[0], where our openhands.py launcher shadows the pip openhands
# namespace package. When run as a module (-m), cwd is used instead.
# Handle both cases by removing the script's parent dir if present.
_script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path = [p for p in sys.path if os.path.abspath(p) != _script_dir]


def _clean_env_for_tmux():
    """Remove bulky SLURM/Cray/module env vars to prevent tmux 'command too long'.

    OpenHands SDK passes os.environ to tmux new_session -e flags. On Perlmutter
    compute nodes, the environment has hundreds of SLURM_*, CRAY_*, and module
    vars that make the tmux command line exceed the limit. We preserve only
    the vars the agent actually needs.
    """
    keep_prefixes = (
        "HOME", "USER", "PATH", "SHELL", "TERM", "LANG", "LC_",
        "VIRTUAL_ENV", "PYTHONPATH", "PYTHON",
        "OPENAI_", "CODEX_", "ANTHROPIC_",
        "CUDA", "LD_LIBRARY_PATH", "LIBRARY_PATH",
        "SWEAGENT_", "SWE_AGENT_",
        "KRIPKE_", "LAGHOS_", "LULESH_", "QUICKSILVER_",
        "INSIDE_BATCH_RUN", "HF_HOME", "XDG_",
        "OPENMPI", "MPI", "OMPI_",
    )
    to_remove = [k for k in os.environ if not any(k.startswith(p) for p in keep_prefixes)]
    for k in to_remove:
        del os.environ[k]


def main():
    parser = argparse.ArgumentParser(description="OpenHands SDK headless runner")
    parser.add_argument("--model", required=True, help="Model name (litellm format)")
    parser.add_argument("--workspace", required=True, help="Working directory")
    parser.add_argument("--prompt-file", required=True, help="Path to prompt file")
    parser.add_argument("--trajectory-file", required=True, help="Output trajectory JSONL")
    parser.add_argument("--max-iterations", type=int, default=50, help="Max agent iterations")
    parser.add_argument("--api-base", default=None, help="API base URL (overrides env)")
    parser.add_argument("--api-key", default=None, help="API key (overrides env)")
    args = parser.parse_args()

    # Clean env vars before OpenHands SDK copies them to tmux -e flags
    _clean_env_for_tmux()

    # Register tools before creating agent
    from openhands.tools.terminal import TerminalTool  # noqa: F401
    from openhands.tools.file_editor import FileEditorTool  # noqa: F401

    from openhands.sdk import LLM, Agent, Tool
    from openhands.sdk.conversation import LocalConversation
    from openhands.sdk.workspace import LocalWorkspace
    from pydantic import SecretStr

    # Read prompt
    with open(args.prompt_file) as f:
        prompt = f.read()

    # Configure LLM
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    api_base = args.api_base or os.environ.get("OPENAI_API_BASE", "")

    llm = LLM(
        model=args.model,
        api_key=SecretStr(api_key),
        base_url=api_base,
        max_output_tokens=4096,
        native_tool_calling=True,
    )

    # Set terminal no-change timeout to 10 minutes (default 30s is too short for
    # HPC builds and benchmarks — laghos_run/qs_run take 60-120s with no output)
    tools = [
        Tool(name="terminal", params={"no_change_timeout_seconds": 600}),
        Tool(name="file_editor"),
    ]
    agent = Agent(llm=llm, tools=tools)
    ws = LocalWorkspace(working_dir=args.workspace)

    conv = LocalConversation(
        agent=agent,
        workspace=ws,
        max_iteration_per_run=args.max_iterations,
    )

    print(f"[OpenHands Runner] Conversation: {conv.id}", file=sys.stderr)
    print(f"[OpenHands Runner] Workspace: {args.workspace}", file=sys.stderr)
    print(f"[OpenHands Runner] Model: {args.model}", file=sys.stderr)

    # Send prompt and run
    conv.send_message(prompt)
    conv.run()

    print(f"[OpenHands Runner] Execution complete: {conv.state.execution_status}", file=sys.stderr)

    # Write trajectory
    with open(args.trajectory_file, "w") as f:
        f.write(json.dumps({
            "status": str(conv.state.execution_status),
            "conversation_id": str(conv.id),
        }) + "\n")

    conv.close()


if __name__ == "__main__":
    main()
