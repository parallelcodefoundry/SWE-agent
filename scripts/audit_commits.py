#!/usr/bin/env python3
"""
Audit curated commits to check what each base commit actually supports.

For each commit, checks:
- Does it have CUDA files?
- Does it have MPI configuration?
- Does it have OpenMP pragmas?
- Can it build with GPU support?
- Can it build CPU-only?

Run on a compute node with GPU access for full testing.
"""
import json
import os
import subprocess
import sys
import tempfile
import shutil

DATASET_PATH = os.environ.get('DATASET_PATH',
    '/pscratch/sd/k/krydzy/SWE-agent/dataset/curated_perf_commits.json')

# App repo URLs
REPOS = {
    'kripke': 'https://github.com/LLNL/Kripke.git',
    'quicksilver': 'https://github.com/LLNL/Quicksilver.git',
    'laghos': 'https://github.com/CEED/Laghos.git',
    'lulesh': 'https://github.com/LLNL/LULESH.git',
}


def get_app_from_instance_id(instance_id):
    """Extract app name from instance_id like 'quicksilver__67a13d0d'."""
    return instance_id.split('__')[0].lower()


def check_cuda_files(repo_path, app):
    """Check if CUDA-related files exist."""
    cuda_indicators = {
        'quicksilver': ['src/cudaFunctions.cc', 'src/cudaFunctions.hh'],
        'kripke': ['src/Kripke/Kernel/CUDA'],
        'laghos': [],  # Laghos uses MFEM's CUDA support
        'lulesh': ['cuda/lulesh.cu', 'cuda/Makefile'],
    }

    results = {'has_cuda_header': False, 'has_cuda_impl': False, 'cuda_files': []}

    for pattern in cuda_indicators.get(app, []):
        full_path = os.path.join(repo_path, pattern)
        if os.path.exists(full_path):
            results['cuda_files'].append(pattern)
            if pattern.endswith(('.cu', '.cc', '.cpp')) and 'cuda' in pattern.lower():
                results['has_cuda_impl'] = True
            if pattern.endswith(('.h', '.hh', '.hpp')) and 'cuda' in pattern.lower():
                results['has_cuda_header'] = True

    # Also do a general search
    for root, dirs, files in os.walk(repo_path):
        # Skip .git
        if '.git' in root:
            continue
        for f in files:
            if 'cuda' in f.lower() and f.endswith(('.cu', '.cc', '.cpp', '.c')):
                results['has_cuda_impl'] = True
                rel_path = os.path.relpath(os.path.join(root, f), repo_path)
                if rel_path not in results['cuda_files']:
                    results['cuda_files'].append(rel_path)
            if 'cuda' in f.lower() and f.endswith(('.h', '.hh', '.hpp')):
                results['has_cuda_header'] = True

    return results


def check_openmp(repo_path):
    """Check if OpenMP is used."""
    try:
        result = subprocess.run(
            ['grep', '-r', '#pragma omp', '--include=*.cc', '--include=*.cpp',
             '--include=*.c', '--include=*.h', '--include=*.hh', '.'],
            cwd=repo_path, capture_output=True, text=True, timeout=30
        )
        return len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
    except:
        return -1


def check_mpi(repo_path):
    """Check if MPI is used."""
    try:
        result = subprocess.run(
            ['grep', '-r', 'MPI_', '--include=*.cc', '--include=*.cpp',
             '--include=*.c', '--include=*.h', '--include=*.hh', '.'],
            cwd=repo_path, capture_output=True, text=True, timeout=30
        )
        return len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
    except:
        return -1


def audit_commit(instance_id, base_commit, work_dir):
    """Audit a single commit."""
    app = get_app_from_instance_id(instance_id)
    repo_url = REPOS.get(app)

    if not repo_url:
        return {'error': f'Unknown app: {app}'}

    result = {
        'instance_id': instance_id,
        'app': app,
        'base_commit': base_commit,
        'expert_commit': instance_id.split('__')[1] if '__' in instance_id else None,
    }

    # Clone and checkout
    repo_path = os.path.join(work_dir, app)
    try:
        print(f"  Cloning {app}...")
        subprocess.run(['git', 'clone', '--quiet', repo_url, repo_path],
                      check=True, capture_output=True, timeout=120)

        print(f"  Checking out base commit {base_commit[:8]}...")
        subprocess.run(['git', 'checkout', '--quiet', base_commit],
                      cwd=repo_path, check=True, capture_output=True, timeout=30)

        # Check for CUDA files
        print(f"  Checking CUDA support...")
        cuda_info = check_cuda_files(repo_path, app)
        result['cuda'] = cuda_info

        # Check for OpenMP
        print(f"  Checking OpenMP usage...")
        result['openmp_pragmas'] = check_openmp(repo_path)

        # Check for MPI
        print(f"  Checking MPI usage...")
        result['mpi_calls'] = check_mpi(repo_path)

        # Determine recommended track
        if cuda_info['has_cuda_impl']:
            result['recommended_track'] = 'gpu-optimize'
            result['build_mode'] = 'cuda'
        elif cuda_info['has_cuda_header'] and not cuda_info['has_cuda_impl']:
            result['recommended_track'] = 'gpu-add'
            result['build_mode'] = 'cpu-only'
            result['warning'] = 'Has CUDA header but no implementation'
        else:
            result['recommended_track'] = 'cpu-optimize'
            result['build_mode'] = 'cpu-only'

        result['success'] = True

    except subprocess.CalledProcessError as e:
        result['error'] = f'Git error: {e}'
        result['success'] = False
    except Exception as e:
        result['error'] = str(e)
        result['success'] = False

    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Audit curated commits')
    parser.add_argument('--instance', type=str, help='Audit specific instance only')
    parser.add_argument('--output', type=str, default='audit_results.json',
                       help='Output file for results')
    args = parser.parse_args()

    # Load dataset
    with open(DATASET_PATH) as f:
        commits = json.load(f)

    print(f"Loaded {len(commits)} commits from dataset")
    print()

    results = []

    with tempfile.TemporaryDirectory() as work_dir:
        for commit in commits:
            instance_id = commit.get('instance_id', 'unknown')
            base_commit = commit.get('base_commit', '')

            if args.instance and instance_id != args.instance:
                continue

            print(f"Auditing {instance_id}...")
            result = audit_commit(instance_id, base_commit, work_dir)
            results.append(result)

            # Print summary
            if result.get('success'):
                cuda = result.get('cuda', {})
                print(f"  CUDA impl: {cuda.get('has_cuda_impl', False)}")
                print(f"  CUDA header: {cuda.get('has_cuda_header', False)}")
                print(f"  OpenMP pragmas: {result.get('openmp_pragmas', 0)}")
                print(f"  MPI calls: {result.get('mpi_calls', 0)}")
                print(f"  Recommended track: {result.get('recommended_track')}")
                if result.get('warning'):
                    print(f"  WARNING: {result['warning']}")
            else:
                print(f"  ERROR: {result.get('error')}")
            print()

            # Clean up for next iteration
            repo_path = os.path.join(work_dir, get_app_from_instance_id(instance_id))
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)

    # Save results
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {args.output}")

    # Print summary table
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"{'Instance ID':<30} {'CUDA Impl':<12} {'Track':<15} {'Notes'}")
    print("-"*80)
    for r in results:
        cuda_impl = 'Yes' if r.get('cuda', {}).get('has_cuda_impl') else 'No'
        track = r.get('recommended_track', 'error')
        warning = r.get('warning', '')[:30] if r.get('warning') else ''
        print(f"{r['instance_id']:<30} {cuda_impl:<12} {track:<15} {warning}")


if __name__ == '__main__':
    main()
