"""
Hatchet analysis utilities for SWE-agent
Provides functions to analyze HPCToolkit profiling data and generate LLM-friendly output
"""

import sys
import os
import glob
import xml.etree.ElementTree as ET
from io import StringIO
from typing import Optional, Dict, Tuple


def parse_hpcstruct_line_ranges(database_dir: str) -> Dict[str, Tuple[str, int, int]]:
    """
    Parse hpcstruct XML files to extract function line ranges.

    Returns a dict mapping function names to (filename, start_line, end_line).
    """
    func_line_ranges = {}

    # Find the measurements directory (sibling to database)
    base_dir = os.path.dirname(database_dir.rstrip('/'))
    measurements_dir = os.path.join(base_dir, 'measurements')
    structs_dir = os.path.join(measurements_dir, 'structs')

    if not os.path.exists(structs_dir):
        # Try relative to database
        structs_dir = os.path.join(database_dir, '..', 'measurements', 'structs')

    if not os.path.exists(structs_dir):
        return func_line_ranges

    # Find all .hpcstruct files
    struct_files = glob.glob(os.path.join(structs_dir, '*.hpcstruct'))

    for struct_file in struct_files:
        try:
            tree = ET.parse(struct_file)
            root = tree.getroot()

            # Process all File elements
            for file_elem in root.iter('F'):
                filename = file_elem.get('n', '')
                if not filename:
                    continue

                # Get just the basename
                basename = os.path.basename(filename)

                # Process all Procedure elements in this file
                for proc_elem in file_elem.iter('P'):
                    proc_name = proc_elem.get('n', '')
                    if not proc_name:
                        continue

                    # Get start line from 'l' attribute
                    try:
                        start_line = int(proc_elem.get('l', 0))
                    except (ValueError, TypeError):
                        start_line = 0

                    if start_line == 0:
                        continue

                    # Find max line from all child Statement elements
                    end_line = start_line
                    for stmt in proc_elem.iter('S'):
                        try:
                            stmt_line = int(stmt.get('l', 0))
                            if stmt_line > end_line:
                                end_line = stmt_line
                        except (ValueError, TypeError):
                            pass

                    # Also check Alien elements for inlined code
                    for alien in proc_elem.iter('A'):
                        try:
                            alien_line = int(alien.get('l', 0))
                            if alien_line > end_line:
                                end_line = alien_line
                        except (ValueError, TypeError):
                            pass

                    # Store the mapping
                    func_line_ranges[proc_name] = (basename, start_line, end_line)

        except ET.ParseError:
            continue
        except Exception:
            continue

    return func_line_ranges


def format_time(seconds: float) -> str:
    """Format time in seconds to human-readable string"""
    if seconds >= 1.0:
        return f"{seconds:.3f}s"
    elif seconds >= 0.001:
        return f"{seconds*1000:.3f}ms"
    elif seconds >= 0.000001:
        return f"{seconds*1000000:.3f}us"
    else:
        return f"{seconds*1000000000:.3f}ns"


def get_metric_column(gf, metric: str) -> str:
    """Get the actual metric column name, handling HPCToolkit conventions"""
    df = gf.dataframe

    # If metric already exists, return it
    if metric in df.columns:
        return metric

    # HPCToolkit uses "time (inc)" for inclusive time
    # Try to find the inclusive version
    metric_inc = f"{metric} (inc)"
    if metric_inc in df.columns:
        return metric_inc

    # Return original if nothing found
    return metric


def analyze_hot_path(gf, metric: str = "time") -> str:
    """Analyze and return hot path information"""
    output = StringIO()
    output.write("## Hot Path Analysis\n\n")
    output.write("Critical execution path (most time-consuming):\n\n")

    try:
        # Determine the metric column to use (hot_path prefers inclusive metrics)
        metric_col = get_metric_column(gf, metric)

        # Get hot path (returns list of nodes, not GraphFrame)
        hot_path_nodes = gf.hot_path(metric=metric_col)

        if not hot_path_nodes:
            output.write("No hot path found.\n")
            return output.getvalue()

        # Print the hot path as a sequence
        output.write(f"Hot path ({len(hot_path_nodes)} nodes):\n\n")
        for i, node in enumerate(hot_path_nodes):
            func_name = node.frame.get('name', '<unknown>')

            # Get metric value for this node if available
            try:
                node_metric = gf.dataframe.loc[node, metric_col]
                if hasattr(node_metric, 'mean'):  # Multi-rank case
                    metric_val = node_metric.mean()
                else:
                    metric_val = node_metric

                if "time" in metric_col.lower():
                    output.write(f"  {i+1}. {func_name:60s} ({format_time(metric_val)})\n")
                else:
                    output.write(f"  {i+1}. {func_name:60s} ({metric_val:,.0f})\n")
            except:
                output.write(f"  {i+1}. {func_name}\n")

        output.write("\n")

    except Exception as e:
        output.write(f"Unable to compute hot path: {str(e)}\n")
        import traceback
        output.write(f"Details: {traceback.format_exc()}\n")

    return output.getvalue()


def analyze_function_ranking(gf, metric: str = "time", top_n: int = 20) -> str:
    """Analyze and return top functions by metric"""
    output = StringIO()
    output.write(f"## Top {top_n} Functions by {metric.title()}\n\n")

    try:
        # Get dataframe and actual metric column
        df = gf.dataframe
        metric_col = get_metric_column(gf, metric)

        # Check if metric exists
        if metric_col not in df.columns:
            available_metrics = [col for col in df.columns if col not in ['name', 'node', 'rank', 'thread', 'nid', 'file', 'module', 'type', 'line']]
            output.write(f"Metric '{metric}' not found. Available metrics: {', '.join(available_metrics)}\n")
            return output.getvalue()

        # Group by node and sum metrics
        by_function = df.groupby(level='node')[metric_col].sum().sort_values(ascending=False)

        # Get total for percentage calculation
        total_value = by_function.sum()

        # Print top functions
        for i, (node, value) in enumerate(by_function.head(top_n).items(), 1):
            percentage = (value / total_value * 100) if total_value > 0 else 0
            # Get function name from node
            func_name = node.frame.get('name', 'unknown') if hasattr(node, 'frame') else str(node)

            if "time" in metric_col.lower():
                output.write(f"{i:2d}. {func_name:60s} {percentage:6.2f}% ({format_time(value)})\n")
            else:
                output.write(f"{i:2d}. {func_name:60s} {percentage:6.2f}% ({value:,.0f})\n")

        output.write(f"\nTotal {metric_col}: ")
        if "time" in metric_col.lower():
            output.write(f"{format_time(total_value)}\n")
        else:
            output.write(f"{total_value:,.0f}\n")

    except Exception as e:
        output.write(f"Unable to compute function ranking: {str(e)}\n")
        import traceback
        output.write(f"Details: {traceback.format_exc()}\n")

    return output.getvalue()


def analyze_load_imbalance(gf, metric: str = "time") -> str:
    """Analyze and return load imbalance information"""
    output = StringIO()
    output.write("## Load Imbalance Analysis\n\n")

    try:
        # Check if this is a multi-rank profile
        df = gf.dataframe
        metric_col = get_metric_column(gf, metric)

        if 'rank' in df.index.names:
            ranks = df.index.get_level_values('rank').unique()
            num_ranks = len(ranks)

            if num_ranks > 1:
                # Compute load imbalance (returns new GraphFrame with .imbalance columns)
                imbalance_gf = gf.load_imbalance(metric_column=metric_col, verbose=False)

                output.write(f"Number of MPI ranks: {num_ranks}\n")
                output.write(f"Metric analyzed: {metric_col}\n\n")

                # Get imbalance column name
                imbalance_col = f"{metric_col}.imbalance"

                # Print top imbalanced functions
                if imbalance_col in imbalance_gf.dataframe.columns:
                    imbalance_by_func = imbalance_gf.dataframe.groupby(level='node')[imbalance_col].mean().sort_values(ascending=False)

                    output.write("Top 10 most imbalanced functions (imbalance ratio = max/mean):\n\n")
                    for i, (node, imb_value) in enumerate(imbalance_by_func.head(10).items(), 1):
                        func_name = node.frame.get('name', 'unknown') if hasattr(node, 'frame') else str(node)
                        output.write(f"  {i:2d}. {func_name:50s} {imb_value:6.3f}x\n")
                    output.write("\n")
                else:
                    output.write("Load imbalance calculation completed but column not found in result.\n")

            else:
                output.write("Single rank profile - load imbalance analysis not applicable\n")
        else:
            output.write("No rank information found - single process execution\n")

    except Exception as e:
        output.write(f"Unable to compute load imbalance: {str(e)}\n")
        output.write("Note: Load imbalance analysis requires multi-rank profiling data\n")
        import traceback
        output.write(f"Details: {traceback.format_exc()}\n")

    return output.getvalue()


def analyze_call_tree(gf, metric: str = "time", max_depth: int = 10) -> str:
    """Analyze and return call tree summary"""
    output = StringIO()
    output.write("## Call Tree Summary\n\n")

    try:
        metric_col = get_metric_column(gf, metric)
        output.write(f"Hierarchical calling context (metric: {metric_col}, max depth: {max_depth}):\n\n")

        # Print tree with metric (depth parameter is actually named 'depth' in tree())
        tree_str = gf.tree(metric_column=metric_col, precision=3, depth=max_depth)
        output.write(tree_str)
        output.write("\n")

    except Exception as e:
        output.write(f"Unable to generate call tree: {str(e)}\n")
        import traceback
        output.write(f"Details: {traceback.format_exc()}\n")

    return output.getvalue()


def analyze_source_locations(gf, metric: str = "time", database_dir: str = None) -> str:
    """Analyze and return source file:line information for hotspots"""
    output = StringIO()
    output.write("## Source Location Analysis\n\n")
    output.write("GPU kernel and function hotspots with source locations:\n\n")

    try:
        df = gf.dataframe.reset_index()
        metric_col = get_metric_column(gf, metric)

        # Parse hpcstruct files to get full line ranges (start-end)
        hpcstruct_ranges = {}
        if database_dir:
            hpcstruct_ranges = parse_hpcstruct_line_ranges(database_dir)

        # Build function-to-source mapping by traversing the call tree
        # This finds the source line that is a child of each function node
        func_to_source = {}

        def find_source_for_functions(node, parent_func=None):
            """Traverse tree to map functions to their source locations"""
            name = node.frame.get('name', '<unknown>')
            file_info = str(node.frame.get('file', ''))
            try:
                line_info = int(node.frame.get('line', 0))
            except:
                line_info = 0
            typ = node.frame.get('type', '')

            # Track current function
            current_func = parent_func
            if typ == 'function':
                current_func = name

            # If this is a line entry with real source info, associate with parent function
            if typ == 'line' and line_info > 0 and '/' in file_info:
                if current_func and current_func not in func_to_source:
                    # Clean up file path
                    clean_file = file_info.replace('src/', '') if file_info.startswith('src/') else file_info
                    filename = clean_file.split('/')[-1]
                    func_to_source[current_func] = (filename, line_info, clean_file)

            for child in node.children:
                find_source_for_functions(child, current_func)

        # Traverse all roots
        for root in gf.graph.roots:
            find_source_for_functions(root)

        # Find function entries with meaningful metric values
        if metric_col in df.columns:
            func_entries = df[(df['type'] == 'function') & (df[metric_col] > 0)].copy()

            if len(func_entries) == 0:
                output.write("No function entries with profiling data found.\n")
                return output.getvalue()

            # Sort by metric value descending
            func_entries = func_entries.sort_values(metric_col, ascending=False)

            output.write(f"{'Function':<50} {'Time':>12} {'Source Location':<40}\n")
            output.write("-" * 102 + "\n")

            shown = set()
            count = 0
            for _, row in func_entries.iterrows():
                func_name = row.get('name', '<unknown>')
                metric_val = row.get(metric_col, 0)

                # Skip if already shown (avoid duplicates from multi-rank)
                if func_name in shown:
                    continue
                shown.add(func_name)

                # Format metric value
                if "time" in metric_col.lower() or "sec" in metric_col.lower():
                    metric_str = format_time(metric_val)
                else:
                    metric_str = f"{metric_val:,.0f}"

                # Look up source location - prefer hpcstruct ranges for full line info
                source_loc = "N/A"
                if func_name in hpcstruct_ranges:
                    filename, start_line, end_line = hpcstruct_ranges[func_name]
                    if start_line == end_line:
                        source_loc = f"{filename}:{start_line}"
                    else:
                        source_loc = f"{filename}:{start_line}-{end_line}"
                elif func_name in func_to_source:
                    filename, line_num, _ = func_to_source[func_name]
                    source_loc = f"{filename}:{line_num}"

                # Truncate function name if too long
                display_name = func_name[:48] + '..' if len(func_name) > 50 else func_name

                output.write(f"{display_name:<50} {metric_str:>12} {source_loc:<40}\n")

                count += 1
                if count >= 15:  # Limit output
                    break

            output.write("\n")

            # Show all functions with source locations (even if no profiling data)
            # Merge both sources of info
            all_funcs = set(func_to_source.keys()) | set(hpcstruct_ranges.keys())
            if all_funcs:
                output.write("All GPU kernels/functions with source info:\n")
                for func_name in sorted(all_funcs, key=lambda x: x.lower()):
                    # Simplify mangled names for display
                    display_name = func_name
                    if '__nv_static_' in func_name:
                        # Extract the actual function name from mangled CUDA name
                        parts = func_name.split('__')
                        for p in reversed(parts):
                            if p and not p.startswith('nv') and not p.startswith('ZN') and len(p) > 3:
                                display_name = p.split('E')[0] if 'E' in p else p
                                break

                    # Get source info - prefer hpcstruct for full ranges
                    if func_name in hpcstruct_ranges:
                        filename, start_line, end_line = hpcstruct_ranges[func_name]
                        if start_line == end_line:
                            loc = f"{filename}:{start_line}"
                        else:
                            loc = f"{filename}:{start_line}-{end_line}"
                    elif func_name in func_to_source:
                        filename, line_num, _ = func_to_source[func_name]
                        loc = f"{filename}:{line_num}"
                    else:
                        continue

                    # Only show functions from application source (not system libs)
                    # Skip entries from system libraries
                    skip_patterns = [
                        'libhpcrun', 'libcuda', 'libcupti', 'libc.', 'libm.',
                        'elf-init', 'crti.S', 'start.S', 'cplus-dem', 'cp-demangle',
                        'rust-demangle', 'atexit.c', 'device_atomic_functions'
                    ]
                    if any(pat in filename.lower() or pat in func_name.lower() for pat in skip_patterns):
                        continue
                    # Also skip if filename suggests system library
                    if filename.endswith('.S') or '/usr/' in str(hpcstruct_ranges.get(func_name, ('', 0, 0))[0] if func_name in hpcstruct_ranges else ''):
                        continue

                    display_name = display_name[:50] + '..' if len(display_name) > 52 else display_name
                    output.write(f"  {display_name:<53} -> {loc}\n")
                output.write("\n")

        else:
            output.write(f"Metric '{metric_col}' not found in dataframe.\n")

    except Exception as e:
        output.write(f"Unable to analyze source locations: {str(e)}\n")
        import traceback
        output.write(f"Details: {traceback.format_exc()}\n")

    return output.getvalue()


def generate_summary(gf, metric: str = "time", database_dir: str = None) -> str:
    """Generate a complete analysis summary"""
    output = StringIO()

    # Header
    output.write("="*80 + "\n")
    output.write("HPCToolkit Performance Analysis (via Hatchet)\n")
    output.write("="*80 + "\n\n")

    # Get basic statistics
    df = gf.dataframe
    metric_col = get_metric_column(gf, metric)

    output.write("## Profile Overview\n\n")
    output.write(f"Requested metric: {metric}\n")
    output.write(f"Using metric column: {metric_col}\n")

    # Check for rank information
    if 'rank' in df.index.names:
        ranks = df.index.get_level_values('rank').unique()
        output.write(f"Number of ranks: {len(ranks)}\n")

    # Get available metrics
    available_metrics = [col for col in df.columns if col not in ['name', 'node', 'rank', 'thread', 'nid', 'file', 'module', 'type', 'line']]
    output.write(f"Available metrics: {', '.join(available_metrics)}\n\n")

    # Perform all analyses
    output.write(analyze_hot_path(gf, metric))
    output.write("\n")

    output.write(analyze_function_ranking(gf, metric, top_n=20))
    output.write("\n")

    output.write(analyze_source_locations(gf, metric, database_dir))
    output.write("\n")

    output.write(analyze_load_imbalance(gf, metric))
    output.write("\n")

    output.write(analyze_call_tree(gf, metric, max_depth=10))
    output.write("\n")

    # Footer
    output.write("="*80 + "\n")
    output.write("End of Analysis\n")
    output.write("="*80 + "\n")

    return output.getvalue()
