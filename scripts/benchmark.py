#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, statistics, sys, tempfile, time
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from execution_handle_ref import make_cad, ReferenceEngine, SQLiteStore
N=1000; now=2_000_000_000
with tempfile.TemporaryDirectory() as td:
    store=SQLiteStore(pathlib.Path(td)/'bench.db')
    eng=ReferenceEngine(store,sink_id='sink-A',clock=lambda:now)
    lat=[]
    t0=time.perf_counter()
    for i in range(N):
        cad=make_cad(act_type='TOOL_CALL',consequence_class='external',actor='bench',operation='send',arguments={'i':i},destination='api:demo',finality_sink='sink-A',policy_generation=1,now=now,candidate_act_id=f'c{i}',freshness_nonce=f'n{i}')
        eh=eng.issue(cad)
        s=time.perf_counter_ns(); eng.consume_and_commit(cad,eh); lat.append((time.perf_counter_ns()-s)/1e6)
    elapsed=time.perf_counter()-t0
    result={'n':N,'end_to_end_ops_per_s':N/elapsed,'hot_path_ms':{'p50':statistics.median(lat),'p95':sorted(lat)[int(.95*N)-1],'p99':sorted(lat)[int(.99*N)-1],'max':max(lat)},'note':'Local SQLite WAL/FULL durability reference only; not a network or production benchmark.'}
    (ROOT/'results'/'benchmark.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
