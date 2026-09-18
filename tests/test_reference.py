from __future__ import annotations
import concurrent.futures
import copy
import os
import tempfile
import threading
import unittest
from dataclasses import replace

from execution_handle_ref import make_cad, act_digest, ReferenceEngine, SQLiteStore, EFError
from execution_handle_ref.cad import arguments_digest
from execution_handle_ref.crypto import pop_proof
from execution_handle_ref.errors import *
from execution_handle_ref.models import FinalityReceipt

NOW = 2_000_000_000

class Clock:
    def __init__(self, t=NOW): self.t=t
    def __call__(self): return self.t

class ExecutionHandleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "ref.db")
        self.store = SQLiteStore(self.db)
        self.clock = Clock()
        self.workload_key = b"workload-k1-secret"
        self.engine = ReferenceEngine(self.store, sink_id="sink-A", clock=self.clock,
                                      workload_keys={"workload-k1": self.workload_key})

    def tearDown(self):
        self.store.close(); self.tmp.cleanup()

    def cad(self, **overrides):
        kw = dict(act_type="PAYMENT_POST", consequence_class="financial", actor="agent-7",
                  operation="post_payment", arguments={"amount_minor":12500,"currency":"INR","memo":"invoice-44"},
                  destination="acct:beneficiary-A", finality_sink="sink-A", policy_generation=1,
                  purpose="invoice_settlement", jurisdiction_policy_id="IN-fin-1", ttl_s=120, now=NOW,
                  candidate_act_id="cad-001", freshness_nonce="nonce-001")
        kw.update(overrides)
        return make_cad(**kw)

    def expect_code(self, code, fn):
        with self.assertRaises(EFError) as cm: fn()
        self.assertEqual(cm.exception.code, code)

    def test_01_matching_single_use_effectuates(self):
        cad=self.cad(); eh=self.engine.issue(cad)
        r=self.engine.consume_and_commit(cad,eh)
        self.assertEqual(r.decision,"EFFECTUATED"); self.assertEqual(self.store.effect_count(eh.handle_id),1)

    def test_02_second_single_use_is_EF005(self):
        cad=self.cad(); eh=self.engine.issue(cad); self.engine.consume_and_commit(cad,eh)
        self.expect_code(EF005, lambda: self.engine.consume_and_commit(cad,eh))
        self.assertEqual(self.store.effect_count(eh.handle_id),1)

    def test_03_argument_substitution_EF023(self):
        cad=self.cad(); eh=self.engine.issue(cad)
        bad=replace(cad, arguments={**cad.arguments,"amount_minor":99999})
        self.expect_code(EF023, lambda: self.engine.consume_and_commit(bad,eh))
        self.assertEqual(self.store.effect_count(),0)

    def test_04_destination_substitution_EF020(self):
        cad=self.cad(); eh=self.engine.issue(cad)
        bad=replace(cad,destination="acct:attacker",extensions={"mutation":"destination"})
        self.expect_code(EF020, lambda: self.engine.consume_and_commit(bad,eh))

    def test_05_wrong_sink_EF040(self):
        cad=self.cad(); eh=self.engine.issue(cad)
        other=ReferenceEngine(self.store,sink_id="sink-B",clock=self.clock)
        self.expect_code(EF040, lambda: other.consume_and_commit(cad,eh))

    def test_06_expired_handle_EF004(self):
        cad=self.cad(ttl_s=2); eh=self.engine.issue(cad,ttl_s=2); self.clock.t += 3
        self.expect_code(EF004, lambda: self.engine.consume_and_commit(cad,eh))

    def test_07_integrity_broken_handle_EF003(self):
        cad=self.cad(); eh=self.engine.issue(cad); eh.act_digest="00"*32
        self.expect_code(EF003, lambda: self.engine.consume_and_commit(cad,eh))

    def test_08_stale_policy_generation_EF041(self):
        cad=self.cad(); eh=self.engine.issue(cad); self.store.bump_generation("policy")
        self.expect_code(EF041, lambda: self.engine.consume_and_commit(cad,eh))

    def test_09_revoked_handle_EF062(self):
        cad=self.cad(); eh=self.engine.issue(cad); self.store.revoke(eh.handle_id)
        self.expect_code(EF062, lambda: self.engine.consume_and_commit(cad,eh))

    def test_10_revocation_after_early_verify_before_commit_is_blocked(self):
        cad=self.cad(); eh=self.engine.issue(cad); self.assertTrue(self.engine.early_verify_hint(cad,eh))
        def revoke_inside(c):
            c.execute("INSERT INTO revoked(handle_id,revoked) VALUES (?,1)",(eh.handle_id,))
            c.execute("UPDATE generations SET value=value+1 WHERE name='revocation'")
        self.expect_code(EF062, lambda: self.engine.consume_and_commit(cad,eh,inside_hook=revoke_inside))
        self.assertEqual(self.store.effect_count(),0)

    def test_11_caller_supplied_stale_arguments_digest_cannot_override_live_arguments(self):
        cad=self.cad(); eh=self.engine.issue(cad)
        bad=replace(cad,arguments={**cad.arguments,"amount_minor":1},arguments_digest=cad.arguments_digest)
        self.expect_code(EF023, lambda: self.engine.consume_and_commit(bad,eh))

    def test_12_counted_under_limit_then_EF005(self):
        # Use distinct candidate IDs/effects while retaining exact digest is impossible under base exact-act semantics;
        # COUNTED here models repeated commits to distinct sink-local rows via payload but same CAD id is protected by
        # effects PK. For conformance, use a fresh DB effect row by deleting only the demonstration effect between uses.
        cad=self.cad(); eh=self.engine.issue(cad,reuse_policy="COUNTED",max_uses=2)
        self.engine.consume_and_commit(cad,eh)
        with self.store.atomic() as c: c.execute("DELETE FROM effects WHERE candidate_act_id=?",(cad.candidate_act_id,))
        self.engine.consume_and_commit(cad,eh)
        with self.store.atomic() as c: c.execute("DELETE FROM effects WHERE candidate_act_id=?",(cad.candidate_act_id,))
        self.expect_code(EF005, lambda: self.engine.consume_and_commit(cad,eh))

    def test_13_envelope_non_identical_in_range_succeeds(self):
        cad=self.cad(arguments={"amount_minor":100,"currency":"INR"})
        env={"constraints":{"arguments.amount_minor":{"min":1,"max":500},"destination":{"one_of":["acct:beneficiary-A"]}},"allow_identical_replay":False}
        eh=self.engine.issue_envelope(cad,envelope=env)
        c1=replace(cad,candidate_act_id="cad-E1",freshness_nonce="n1",arguments={"amount_minor":100,"currency":"INR"})
        c2=replace(cad,candidate_act_id="cad-E2",freshness_nonce="n2",arguments={"amount_minor":200,"currency":"INR"})
        self.engine.consume_and_commit(c1,eh); self.engine.consume_and_commit(c2,eh)
        self.assertEqual(self.store.effect_count(eh.handle_id),2)

    def test_14_envelope_identical_replay_default_EF006(self):
        cad=self.cad(arguments={"amount_minor":100,"currency":"INR"})
        env={"constraints":{"arguments.amount_minor":{"min":1,"max":500}},"allow_identical_replay":False}
        eh=self.engine.issue_envelope(cad,envelope=env)
        c1=replace(cad,candidate_act_id="cad-E1",freshness_nonce="n1")
        self.engine.consume_and_commit(c1,eh)
        with self.store.atomic() as c: c.execute("DELETE FROM effects WHERE candidate_act_id=?",(c1.candidate_act_id,))
        self.expect_code(EF006, lambda: self.engine.consume_and_commit(c1,eh))

    def test_15_envelope_identical_replay_explicitly_allowed(self):
        cad=self.cad(arguments={"amount_minor":100,"currency":"INR"})
        env={"constraints":{"arguments.amount_minor":{"min":1,"max":500}},"allow_identical_replay":True}
        eh=self.engine.issue_envelope(cad,envelope=env)
        c1=replace(cad,candidate_act_id="cad-E1",freshness_nonce="n1")
        self.engine.consume_and_commit(c1,eh)
        with self.store.atomic() as c: c.execute("DELETE FROM effects WHERE candidate_act_id=?",(c1.candidate_act_id,))
        self.engine.consume_and_commit(c1,eh)

    def test_16_envelope_out_of_range_EF043(self):
        cad=self.cad(arguments={"amount_minor":100,"currency":"INR"})
        env={"constraints":{"arguments.amount_minor":{"min":1,"max":500}},"allow_identical_replay":False}
        eh=self.engine.issue_envelope(cad,envelope=env)
        bad=replace(cad,candidate_act_id="cad-E2",freshness_nonce="n2",arguments={"amount_minor":999,"currency":"INR"})
        self.expect_code(EF043, lambda: self.engine.consume_and_commit(bad,eh))

    def test_17_two_concurrent_workers_only_one_commit(self):
        cad=self.cad(); eh=self.engine.issue(cad)
        barrier=threading.Barrier(2)
        def worker(i):
            barrier.wait()
            try:
                self.engine.consume_and_commit(cad,eh,payload={"worker":i}); return "OK"
            except EFError as e: return e.code
            except Exception as e: return type(e).__name__
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            results=list(ex.map(worker,[1,2]))
        self.assertEqual(results.count("OK"),1,results)
        self.assertEqual(results.count(EF005),1,results)
        self.assertEqual(self.store.effect_count(eh.handle_id),1)

    def test_18_32_way_concurrency_only_one_commit(self):
        cad=self.cad(); eh=self.engine.issue(cad)
        barrier=threading.Barrier(32)
        def worker(i):
            barrier.wait()
            try: self.engine.consume_and_commit(cad,eh,payload={"worker":i}); return "OK"
            except EFError as e: return e.code
            except Exception as e: return type(e).__name__
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex:
            results=list(ex.map(worker,range(32)))
        self.assertEqual(results.count("OK"),1,results)
        self.assertEqual(results.count(EF005),31,results)

    def test_19_crash_after_consume_before_commit_rolls_back_local_transaction(self):
        cad=self.cad(); eh=self.engine.issue(cad)
        with self.assertRaisesRegex(RuntimeError,"SIMULATED_CRASH_AFTER_CONSUME"):
            self.engine.consume_and_commit(cad,eh,crash_point="after_consume_before_commit")
        self.assertEqual(self.store.effect_count(),0)
        self.engine.consume_and_commit(cad,eh)
        self.assertEqual(self.store.effect_count(),1)

    def test_20_receipt_replayed_as_handle_EF002(self):
        cad=self.cad(); eh=self.engine.issue(cad); r=self.engine.consume_and_commit(cad,eh)
        self.expect_code(EF002, lambda: self.engine.present_authority_object(cad,r))

    def test_21_attestation_result_instead_of_handle_EF002(self):
        cad=self.cad(); self.expect_code(EF002, lambda: self.engine.present_authority_object(cad,{"object_type":"attestation_result","valid":True}))

    def test_22_scitt_receipt_instead_of_handle_EF002(self):
        cad=self.cad(); self.expect_code(EF002, lambda: self.engine.present_authority_object(cad,{"object_type":"scitt_receipt"}))

    def test_23_valid_workload_identity_does_not_override_act_mismatch(self):
        cad=self.cad(); eh=self.engine.issue(cad,key_binding="workload-k1")
        new_args={**cad.arguments,"amount_minor":999}
        bad=replace(cad,arguments=new_args,arguments_digest=arguments_digest(new_args))
        proof=pop_proof(eh.handle_id,act_digest(bad),"sink-A",self.workload_key)
        self.expect_code(EF023, lambda: self.engine.consume_and_commit(bad,eh,pop=proof))

    def test_24_key_bound_handle_without_pop_EF012(self):
        cad=self.cad(); eh=self.engine.issue(cad,key_binding="workload-k1")
        self.expect_code(EF012, lambda: self.engine.consume_and_commit(cad,eh))

    def test_25_key_bound_handle_with_pop_succeeds(self):
        cad=self.cad(); eh=self.engine.issue(cad,key_binding="workload-k1")
        proof=pop_proof(eh.handle_id,act_digest(cad),"sink-A",self.workload_key)
        self.engine.consume_and_commit(cad,eh,pop=proof)

    def test_26_consume_store_down_fails_closed_EF081(self):
        cad=self.cad(); eh=self.engine.issue(cad); self.store.available=False
        self.expect_code(EF081, lambda: self.engine.consume_and_commit(cad,eh))

    def test_27_cad_argument_key_order_does_not_change_digest(self):
        c1=self.cad(arguments={"b":2,"a":1}); c2=self.cad(arguments={"a":1,"b":2})
        self.assertEqual(act_digest(c1),act_digest(c2))

    def test_28_unicode_is_stable(self):
        c1=self.cad(arguments={"city":"Kolkata","note":"নমস্কার"}); c2=self.cad(arguments={"note":"নমস্কার","city":"Kolkata"})
        self.assertEqual(act_digest(c1),act_digest(c2))

    def test_29_float_arguments_rejected_by_reference_canonical_profile(self):
        from execution_handle_ref.canonical import CanonicalizationError
        with self.assertRaises(CanonicalizationError): self.cad(arguments={"amount":1.5})

    def test_30_sink_local_reconstruction_recomputes_argument_digest(self):
        cad=self.cad(); bad=replace(cad,arguments_digest="00"*32)
        live=self.engine.reconstruct(bad)
        self.assertEqual(live.arguments_digest,arguments_digest(live.arguments))

    def test_31_alternate_raw_credential_path_demonstrates_path_coverage_limit(self):
        # This test intentionally demonstrates a limitation: if another path writes K without the engine,
        # the protocol cannot prevent it. PASS means the harness detects that the prevention claim is invalid.
        with self.store.atomic() as c:
            c.execute("INSERT INTO effects(candidate_act_id,handle_id,act_digest,payload,committed_at) VALUES (?,?,?,?,?)",
                      ("raw-bypass","RAW-CREDENTIAL","none","{}",NOW))
        self.assertEqual(self.store.effect_count(),1)

    def test_32_policy_correctness_is_out_of_scope(self):
        # A PED can authorize a semantically bad act; correspondence still works. This is a bounded guarantee.
        cad=self.cad(destination="acct:bad-policy-choice"); eh=self.engine.issue(cad)
        self.engine.consume_and_commit(cad,eh)
        self.assertEqual(self.store.effect_count(eh.handle_id),1)

    def test_33_unknown_authority_object_EF002(self):
        cad=self.cad(); self.expect_code(EF002, lambda: self.engine.present_authority_object(cad,"oauth-token"))

    def test_34_tampered_not_bearer_flag_breaks_integrity_EF003(self):
        cad=self.cad(); eh=self.engine.issue(cad); eh.not_bearer_alone=False
        self.expect_code(EF003, lambda: self.engine.consume_and_commit(cad,eh))

    def test_35_counted_max_uses_must_be_positive_EF042(self):
        cad=self.cad(); self.expect_code(EF042, lambda: self.engine.issue(cad,reuse_policy="COUNTED",max_uses=0))

    def test_36_base_envelope_without_explicit_binding_profile_rejected_EF042(self):
        cad=self.cad(); eh=self.engine.issue(cad,reuse_policy="ENVELOPE",envelope={"constraints":{"arguments.amount_minor":{"max":500}}})
        self.expect_code(EF042, lambda: self.engine.consume_and_commit(cad,eh))

if __name__ == "__main__": unittest.main(verbosity=2)
