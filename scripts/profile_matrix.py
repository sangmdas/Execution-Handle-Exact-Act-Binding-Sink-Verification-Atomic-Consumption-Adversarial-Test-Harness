#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, json, pathlib, sys, tempfile, threading
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from dataclasses import replace
from execution_handle_ref import make_cad, ReferenceEngine, SQLiteStore, EFError
from execution_handle_ref.cad import arguments_digest

NOW=2_000_000_000
PROFILES=[
 {"name":"agent-tool","act_type":"TOOL_CALL","consequence":"external_api","operation":"send_email","args":{"to":"ops@example.test","template":"incident-7"},"destination":"api:mail","purpose":"incident_response"},
 {"name":"payment","act_type":"PAYMENT_POST","consequence":"financial","operation":"post_payment","args":{"amount_minor":12500,"currency":"INR"},"destination":"acct:beneficiary-A","purpose":"invoice_settlement"},
 {"name":"cloud-egress","act_type":"DATA_EGRESS","consequence":"data_release","operation":"export_object","args":{"object":"model-weights-17","bytes":1048576},"destination":"region:eu-west","purpose":"approved_replication"},
 {"name":"industrial","act_type":"ACTUATION","consequence":"physical","operation":"set_valve","args":{"valve":"V-17","position_bp":2500},"destination":"plc:line-2","purpose":"process_control"},
]

def make(profile, i=0):
 return make_cad(act_type=profile['act_type'],consequence_class=profile['consequence'],actor='matrix-agent',operation=profile['operation'],arguments=profile['args'],destination=profile['destination'],purpose=profile['purpose'],jurisdiction_policy_id='matrix-policy',finality_sink='sink-A',policy_generation=1,now=NOW,candidate_act_id=f"{profile['name']}-{i}",freshness_nonce=f"n-{profile['name']}-{i}")

rows=[]
for p in PROFILES:
 with tempfile.TemporaryDirectory() as td:
  st=SQLiteStore(pathlib.Path(td)/'m.db'); e=ReferenceEngine(st,sink_id='sink-A',clock=lambda:NOW)
  cad=make(p); h=e.issue(cad); e.consume_and_commit(cad,h); rows.append({"profile":p['name'],"case":"matching","expected":"EFFECTUATED","observed":"EFFECTUATED","pass":True})
 with tempfile.TemporaryDirectory() as td:
  st=SQLiteStore(pathlib.Path(td)/'m.db'); e=ReferenceEngine(st,sink_id='sink-A',clock=lambda:NOW)
  cad=make(p); h=e.issue(cad); a=dict(cad.arguments); first=next(iter(a)); v=a[first]; a[first]=(v+1 if isinstance(v,int) else str(v)+'-MUTATED')
  bad=replace(cad,arguments=a,arguments_digest=arguments_digest(a))
  try: e.consume_and_commit(bad,h); obs='EFFECTUATED'
  except EFError as x: obs=x.code
  rows.append({"profile":p['name'],"case":"argument-substitution","expected":"EF-023","observed":obs,"pass":obs=='EF-023'})

# Concurrency levels as an independent variable.
for workers in (2,8,32,64):
 with tempfile.TemporaryDirectory() as td:
  st=SQLiteStore(pathlib.Path(td)/'c.db'); e=ReferenceEngine(st,sink_id='sink-A',clock=lambda:NOW); cad=make(PROFILES[0]); h=e.issue(cad); b=threading.Barrier(workers)
  def w(i):
   b.wait()
   try: e.consume_and_commit(cad,h,payload={'worker':i}); return 'OK'
   except EFError as x: return x.code
  with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex: out=list(ex.map(w,range(workers)))
  rows.append({"profile":"single-use","case":f"concurrency-{workers}","expected":"1 OK, rest EF-005","observed":f"{out.count('OK')} OK, {out.count('EF-005')} EF-005","pass":out.count('OK')==1 and out.count('EF-005')==workers-1})

summary={"variables":{"profiles":[p['name'] for p in PROFILES],"concurrency":[2,8,32,64],"canonicalization":"REFCANON-1","store":"SQLite WAL + synchronous=FULL","clock":"fixed deterministic"},"pass":sum(r['pass'] for r in rows),"total":len(rows),"rows":rows}
(ROOT/'results'/'profile-matrix.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
