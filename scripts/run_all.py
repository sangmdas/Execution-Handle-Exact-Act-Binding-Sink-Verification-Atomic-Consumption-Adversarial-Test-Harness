#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, platform, shutil, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
os.chdir(ROOT)

def run(cmd):
    p=subprocess.run(cmd,text=True,capture_output=True)
    return {"cmd":" ".join(cmd),"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr}

results={"timestamp_utc":time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
         "system":{"platform":platform.platform(),"machine":platform.machine(),"python":sys.version.split()[0]},"runs":[]}
results["runs"].append(run([sys.executable,"-m","unittest","discover","-s","tests","-v"]))
py=run([sys.executable,"interop/python_digest.py"]); results["runs"].append(py)
if shutil.which("node"): results["runs"].append(run(["node","interop/node_digest.mjs"]))
if shutil.which("go"): results["runs"].append(run(["go","run","interop/go_digest.go"]))
# Cross-language comparison for tools that ran successfully.
digests=[]
for r in results["runs"][1:]:
    if r["returncode"]==0:
        pairs=[line.strip().split() for line in r["stdout"].splitlines() if line.strip()]
        digests.append({a:b for a,b in pairs})
results["interop_equal"] = bool(digests) and all(d==digests[0] for d in digests[1:])
expected=json.loads((ROOT/"test_vectors"/"canonicalization_expected.json").read_text())
results["golden_vectors_match"] = bool(digests) and all(d==expected for d in digests)
out=ROOT/'results'/'latest.json'; out.write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps({"all_returncodes":[r['returncode'] for r in results['runs']],"interop_equal":results['interop_equal'],"golden_vectors_match":results['golden_vectors_match'],"result_file":str(out)},indent=2))
sys.exit(0 if all(r['returncode']==0 for r in results['runs']) and results['interop_equal'] and results['golden_vectors_match'] else 1)
