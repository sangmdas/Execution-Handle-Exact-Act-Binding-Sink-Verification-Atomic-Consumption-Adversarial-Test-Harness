#!/usr/bin/env python3
from __future__ import annotations
import pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from execution_handle_ref import make_cad, ReferenceEngine, SQLiteStore, EFError

def main():
    now=2_000_000_000
    store=SQLiteStore(':memory:')
    engine=ReferenceEngine(store,sink_id='sink-A',clock=lambda:now)
    cad=make_cad(act_type='PAYMENT_POST',consequence_class='financial',actor='agent-7',operation='post_payment',arguments={'amount_minor':12500,'currency':'INR'},destination='acct:beneficiary-A',finality_sink='sink-A',policy_generation=1,now=now,candidate_act_id='demo-1',freshness_nonce='demo-nonce')
    eh=engine.issue(cad)
    print('first:',engine.consume_and_commit(cad,eh).decision)
    try:
        engine.consume_and_commit(cad,eh)
    except EFError as e:
        print('replay:',e.code,e.message)

if __name__=='__main__': main()
