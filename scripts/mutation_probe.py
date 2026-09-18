#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, random, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from dataclasses import replace
from execution_handle_ref import make_cad, act_digest
from execution_handle_ref.cad import arguments_digest

rng=random.Random(0xEFA11)
N=2000
same_reorder=0; changed_mutation=0
unicode_values=['Kolkata','Balasore','নমস্কার','安全','مرحبا','₹','Δ']
for i in range(N):
    items=[('n',rng.randint(-10_000_000,10_000_000)),('flag',bool(rng.getrandbits(1))),('label',rng.choice(unicode_values)),('nested',{'x':rng.randint(0,999),'tags':['a','b',str(i%7)]})]
    rng.shuffle(items); args=dict(items)
    cad=make_cad(act_type='PROBE',consequence_class='test',actor='probe',operation='op',arguments=args,destination='sink-target',finality_sink='sink-A',policy_generation=1,now=2_000_000_000,candidate_act_id=f'p{i}',freshness_nonce=f'n{i}')
    reordered=dict(reversed(list(args.items())))
    cad2=replace(cad,arguments=reordered,arguments_digest=arguments_digest(reordered))
    if act_digest(cad)==act_digest(cad2): same_reorder+=1
    mutated=dict(args); mutated['n']=mutated['n']+1
    cad3=replace(cad,arguments=mutated,arguments_digest=arguments_digest(mutated))
    if act_digest(cad)!=act_digest(cad3): changed_mutation+=1
result={'seed':'0xEFA11','cases':N,'reordered_equivalent_same_digest':same_reorder,'single_argument_mutation_changed_digest':changed_mutation,'pass':same_reorder==N and changed_mutation==N,'note':'Deterministic property probe, not cryptographic collision testing or formal verification.'}
(ROOT/'results'/'mutation-probe.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
