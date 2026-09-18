#!/usr/bin/env python3
import json, hashlib, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from execution_handle_ref.canonical import canonical_bytes
vectors=json.loads((ROOT/'test_vectors/canonicalization_vectors.json').read_text())
for v in vectors:
    print(v['name'], hashlib.sha256(canonical_bytes(v['value'])).hexdigest())
