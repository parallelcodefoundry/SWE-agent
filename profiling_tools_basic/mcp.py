""" An MCP server for the optimization agent tools.
"""
import json
from fastmcp import FastMCP
import typer
from pathlib import Path
from typing import List

from ..config import RunConfig
from .benchmark import BenchmarkTool
from .profile import ProfileTool
from .microbench import MicrobenchTool
from .compiler_analysis import CompilerAnalysisTool
from .file_viewer import FileViewerTool
from .list_dir import ListDirTool
from .search import SearchTool


app = typer.Typer(add_completion=False)

AVAILABLE_TOOL_CLS = {
    "benchmark_code": BenchmarkTool,
    #"profile_code": ProfileTool,
    "microbench_code": MicrobenchTool,
    "compiler_analysis": CompilerAnalysisTool,
    "file_viewer": FileViewerTool,
    "list_dir": ListDirTool,
    "search": SearchTool,
}

def get_tools(cfg, tools: List[str] | str = "all"):
    if tools == "all":
        return [cls(cfg) for cls in AVAILABLE_TOOL_CLS.values()]
    
    selected = []
    for name in tools.split(","):
        name = name.strip()
        if name in AVAILABLE_TOOL_CLS:
            selected.append(AVAILABLE_TOOL_CLS[name](cfg))
        else:
            raise ValueError(f"Unknown tool: {name}")
    return selected


def register_tools(mcp, cfg, tools: List[str] | str = "all"):
    tools = get_tools(cfg, tools)

    for t in tools:
        t.register_mcp_tool(mcp)

@app.command()
def inspect():
    ### print all available tools
    for tool in AVAILABLE_TOOL_CLS.values():
        print(f"Tool: {tool.name}, Description: {tool.description}")

@app.command()
def serve(
    program_dir: Path = typer.Option(..., exists=True, file_okay=False, dir_okay=True, help="Path to app directory"),
    file: Path = typer.Option(..., help="Path to file within program_dir to patch"),
    start: int = typer.Option(..., help="Start line (1-based) of ROI"),
    end: int = typer.Option(..., help="End line (1-based) of ROI"),
    script: Path = typer.Option(..., help="User script (build+run+benchmark)"),
    profile_script: Path = typer.Option(None, help="Optional separate profiling script"),
    workdir: Path = typer.Option(Path("./gpu_opt_runs"), help="Output working directory"),
    env_vars: str = typer.Option("{}", help="Additional environment variables"),
    gpu_ids: str = typer.Option("0", help="CUDA_VISIBLE_DEVICES list"),
    transport: str = typer.Option("stdio", help="stdio | streamable-http | sse"),
    tools: str = typer.Option("all", help="comma-separated list of tools to enable"),
    host: str = typer.Option("127.0.0.1", help="Host for streamable-http or sse transport"),
    port: int = typer.Option(8000, help="Port for streamable-http or sse transport"),
):
    config = RunConfig(
        program_dir=program_dir.resolve(),
        file=file,
        start_line=start,
        end_line=end,
        script=script,
        profile_script=profile_script,
        workdir=workdir.resolve(),
        gpu_ids=gpu_ids,
        env_vars=json.loads(env_vars or "{}"),
    )

    server = FastMCP("gpu-opt-agent")
    register_tools(server, config, tools=tools)
    server.run(transport=transport, host=host, port=port)
    

if __name__ == "__main__":
    app()