"""CLI: freeze verification, execution, raw-only analysis and reproduction."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
from importlib.metadata import version

from .execution import CONDITIONS, canonical, run_trial
from ..metrics.aggregate import analyze
from ..tasks.catalog import load_tasks


def verify_lock(root):
    lock_path = root/"experiments/E001_deterministic_baseline/config/protocol-lock.json"
    lock = json.loads(lock_path.read_text())
    for relative, expected in lock["files"].items():
        actual = sha256((root/relative).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("Frozen definition changed: " + relative)
    return sha256(lock_path.read_bytes()).hexdigest()


def execute(root, output, protocol_commit):
    lock_digest = verify_lock(root)
    if len(protocol_commit) != 40 or any(c not in "0123456789abcdef" for c in protocol_commit):
        raise ValueError("Supply the frozen Git commit SHA")
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Refusing to overwrite raw results")
    (output/"traces").mkdir(parents=True, exist_ok=True)
    rows = []
    for condition in CONDITIONS:
        for task in load_tasks():
            row, trace = run_trial(task, condition, experiment_id="E001")
            row["protocol_commit"] = protocol_commit
            row["protocol_lock_sha256"] = lock_digest
            (output/row["trace_file"]).write_text(canonical(trace))
            rows.append(row)
    (output/"results.jsonl").write_text("".join(canonical(row) for row in rows))
    manifest = dict(experiment_id="E001", benchmark_version="0.1.0", trials=len(rows), protocol_commit=protocol_commit,
                    protocol_lock_sha256=lock_digest, python=platform.python_version(),
                    dependencies={p:version(p) for p in ("jsonschema", "rfc3339-validator", "pytest")},
                    files={str(p.relative_to(output)):sha256(p.read_bytes()).hexdigest()
                           for p in sorted(output.rglob("*")) if p.is_file()})
    (output/"manifest.json").write_text(canonical(manifest))
    return manifest


def verify_raw(output):
    output=Path(output)
    manifest=json.loads((output/"manifest.json").read_text())
    actual_paths={str(p.relative_to(output)) for p in output.rglob("*") if p.is_file()} - {"manifest.json"}
    if actual_paths != set(manifest["files"]):
        raise ValueError("Raw file inventory differs")
    for path, expected in manifest["files"].items():
        if sha256((output/path).read_bytes()).hexdigest() != expected:
            raise ValueError("Raw artifact differs: "+path)
    rows=[json.loads(line) for line in (output/"results.jsonl").read_text().splitlines()]
    if len(rows) != manifest["trials"]:
        raise ValueError("Trial count differs")
    for row in rows:
        if sha256((output/row["trace_file"]).read_bytes()).hexdigest() != row["trace_sha256"]:
            raise ValueError("Trial trace differs")
    return manifest


def main():
    parser=argparse.ArgumentParser(__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    run=sub.add_parser("run")
    run.add_argument("--root",type=Path,default=Path.cwd())
    run.add_argument("--output",required=True,type=Path)
    run.add_argument("--protocol-commit",required=True)
    analysis=sub.add_parser("analyze")
    analysis.add_argument("--raw",required=True,type=Path)
    analysis.add_argument("--output",required=True,type=Path)
    verify=sub.add_parser("verify")
    verify.add_argument("first",type=Path)
    verify.add_argument("second",type=Path,nargs="?")
    args=parser.parse_args()
    if args.command == "run":
        manifest=execute(args.root,args.output,args.protocol_commit)
        print(f"E001: {manifest['trials']} trials; raw artifacts written to {args.output}")
    elif args.command == "analyze":
        analyze(args.raw,args.output)
        print("Analysis generated from raw rows only")
    else:
        one=verify_raw(args.first)
        if args.second:
            two=verify_raw(args.second)
            if one != two:
                raise ValueError("Independent runs differ")
        print("Raw hashes and trace links verified" + ("; independent runs identical" if args.second else ""))

if __name__ == "__main__":
    main()
