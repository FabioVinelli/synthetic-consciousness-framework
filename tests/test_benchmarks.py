"""Development/pilot fixtures only; E001 is executed after the protocol commit."""
from copy import deepcopy
import builtins
import json
from pathlib import Path

import pytest

from benchmarks.conditions.common import BUDGET, Environment, new_behavior
from benchmarks.conditions import baselines
from benchmarks.metrics.aggregate import analyze, summarize
from benchmarks.metrics.scoring import score
from benchmarks.runner.execution import CONDITIONS, canonical, digest, run_trial
from benchmarks.tasks.catalog import load_tasks, public_task

ROOT = Path(__file__).parents[1]


def task(family):
    return next(t for t in load_tasks() if t['task_id'] == family+'-A')


def test_b0_b1_independent_of_cafh(monkeypatch):
    original = builtins.__import__
    def restricted(name, *args, **kwargs):
        assert not name.startswith('cafh')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', restricted)
    for agentic in (False, True):
        t=task('T6')
        result=baselines.execute(public_task(t), Environment(t['environment']), agentic=agentic)
        assert result['resources']['cycles']==2
        assert result['resources']['memory_operations'] > 0 if agentic else result['resources']['memory_operations']==0


def test_b1_ordinary_memory_and_recovery():
    assert run_trial(task('T6'), 'B1')[0]['memory_hits']==1
    assert run_trial(task('T11'), 'B1')[0]['successful_recoveries']==1
    assert run_trial(task('T11'), 'B0')[0]['success'] is False


def test_all_conditions_identical_public_environment_and_task():
    rows=[run_trial(task('T1'), c)[0] for c in CONDITIONS]
    for key in ('task_digest','environment_digest','public_context_digest'):
        assert len({r[key] for r in rows})==1
    assert all(r['configuration']['budget']==BUDGET for r in rows)


def test_public_policy_context_excludes_oracle_and_condition():
    p=public_task(task('T6'))
    assert set(vars(p))=={'objective','allowed_actions','steps'}
    assert 'token:A' not in repr(p)


@pytest.mark.parametrize('condition',CONDITIONS)
def test_deterministic_pilot_reruns(condition):
    first=run_trial(task('T4'),condition)
    assert first==run_trial(task('T4'),condition)


def test_scoring_is_deterministic_and_does_not_mutate():
    _,b=run_trial(task('T4'),'B0')
    before=deepcopy(b)
    assert score(task('T4'),b)==score(task('T4'),b)
    assert b==before


def test_unsupported_claim_count_and_rejection_not_success():
    assert run_trial(task('T3'),'B0')[0]['unsupported_claims']==1
    row,behavior=run_trial(task('T3'),'C1-full')
    assert row['unsupported_claims']==0
    assert row['runtime_failed'] and not row['success']
    assert behavior['final_state']['status']=='failed'


def test_appropriate_and_inappropriate_abstention():
    assert run_trial(task('T1'),'B0')[0]['appropriate_abstentions']==1
    assert run_trial(task('T6'),'B0')[0]['inappropriate_abstentions']==1


def test_memory_fabrication_detected():
    b=new_behavior()
    b['memories_used']=[dict(cycle=1,statement='invented memory')]
    assert score(task('T7'),b)['fabricated_memories']==1
    assert not score(task('T7'),b)['success']


@pytest.mark.parametrize('condition',['B0','B1','C1-full'])
def test_contradictory_reports_preserved(condition):
    row,b=run_trial(task('T2'),condition)
    assert row['contradictions_detected']==1 and row['contradictions_missed']==0
    b['reports'].pop()
    assert score(task('T2'),b)['contradictions_missed']==1
    assert not score(task('T2'),b)['success']


def test_mismatch_and_missed_mismatch_scoring():
    row,b=run_trial(task('T4'),'C1-full')
    assert row['prediction_mismatches_detected']==1 and row['explicit_revisions']==1
    b['comparisons'][0]['mismatch_detected']=False
    assert score(task('T4'),b)['prediction_mismatches_missed']==1
    assert not score(task('T4'),b)['success']


def test_match_has_no_revision():
    row,_=run_trial(task('T5'),'C1-full')
    assert row['prediction_matches']==1 and row['explicit_revisions']==0
    assert row['success']


def test_error_recovery_score_requires_observed_fallback():
    row,b=run_trial(task('T11'),'B1')
    assert row['successful_recoveries']==1
    b['comparisons']=[]
    assert score(task('T11'),b)['successful_recoveries']==0


def test_policy_violation_scoring():
    row,b=run_trial(task('T10'),'B0')
    assert row['policy_violations']==0 and row['success']
    b['actions']=[dict(cycle=1,name='forbidden',argument='A')]
    assert score(task('T10'),b)['policy_violations']==1
    assert not score(task('T10'),b)['success']


@pytest.mark.parametrize('condition',CONDITIONS)
def test_resource_counts_present_bounded_and_not_equalized(condition):
    row,_=run_trial(task('T6'),condition)
    assert all(type(row[k]) is int and 0 <= row[k] <= limit for k,limit in BUDGET.items())
    assert row['model_calls'] > 0
    assert row['actions_taken'] > 0


def test_self_model_ablation_disables_population_and_call():
    row,b=run_trial(task('T5'),'C1-no-self-model')
    assert not b['final_state']['self_model']
    assert not b['final_state']['capabilities']
    assert not b['final_state']['limitations']
    assert row['model_calls']==4
    assert any(e['event']=='self_model_disabled' for e in b['trace'])


def test_memory_ablation_disables_storage_retrieval_and_backdoor():
    row,b=run_trial(task('T6'),'C1-no-memory-continuity')
    assert row['memory_hits']==0 and row['memory_operations']==0
    assert not b['final_state']['memory_references']
    assert not any(r['information_class']=='remembered' for r in b['final_state']['beliefs'])
    assert row['inappropriate_abstentions']==1
    assert not row['success']


def test_reflection_ablation_retains_preaction_safety_not_post_revision():
    row,b=run_trial(task('T4'),'C1-no-reflection-revision')
    assert row['explicit_revisions']==0
    assert row['prediction_mismatches_detected']==1  # observation comparison remains
    names=[e['event'] for e in b['trace']]
    assert 'pre_action_reflection' in names and 'post_action_reflection' not in names
    assert 'reflection_revision_disabled' in names


@pytest.mark.parametrize('name',['no-epistemic-monitor','no-consequence-model','no-intentionality'])
def test_blocked_ablation_not_falsely_executed(name):
    from benchmarks.conditions.cafh_condition import BLOCKED,execute
    assert name in BLOCKED
    with pytest.raises(ValueError,match='Unavailable'):
        execute(public_task(task('T1')),Environment(task('T1')['environment']),ablation=name,run_id='pilot')


def test_full_matches_approved_phase3_golden_state_and_every_event():
    from cafh.adapters.mock import MockAdapter,MockEnvironment
    from cafh.runtime.engine import Engine,RuntimeConfig
    e=Engine(MockAdapter(),MockEnvironment(),objective='Regression objective',
             config=RuntimeConfig(allowed_actions=('echo',)),run_id='regression')
    e.run_cycle('first');e.run_cycle('second')
    golden=json.loads((ROOT/'tests/fixtures/phase3_golden.json').read_text())
    assert digest(dict(state=e.state,events=e.trace.events))==golden['sha256']
    assert len(e.trace.events)==golden['events']


def test_c1_staged_trace_and_reference_path():
    from cafh.runtime.cycle import STAGES
    _,b=run_trial(task('T4'),'C1-full')
    events=b['trace']
    assert list(dict.fromkeys(e['stage'] for e in events))==list(STAGES)
    assert [e['sequence'] for e in events]==list(range(len(events)))
    state=b['final_state']; revision=state['model_revisions'][0]
    assert revision['prior_record_reference']==state['predicted_consequences'][0]['id']
    assert revision['trigger_references']==[state['observed_consequences'][0]['id']]
    assert all(e['run_id'] and 'record_references' in e for e in events)


def test_serialization_roundtrip_and_raw_only_aggregation(tmp_path):
    rows=[run_trial(task('T1'),c)[0] for c in ('B0','B1')]
    raw=tmp_path/'results.jsonl'
    raw.write_text(''.join(canonical(r) for r in rows))
    assert canonical(json.loads(canonical(rows)))==canonical(rows)
    expected=summarize(rows)
    assert analyze(raw,tmp_path/'first')==expected
    assert analyze(raw,tmp_path/'second')==expected
    assert (tmp_path/'first/summary.json').read_bytes()==(tmp_path/'second/summary.json').read_bytes()


def test_no_consciousness_metric():
    row,_=run_trial(task('T1'),'B0')
    assert not any('conscious' in key or 'sentien' in key for key in row)
    assert 'success_per_resource' in summarize([row])['conditions']['B0']


def test_benchmark_exception_cannot_be_success(monkeypatch):
    def broken(*args,**kwargs): raise ValueError('fixture defect')
    monkeypatch.setattr(baselines,'execute',broken)
    row,_=run_trial(task('T1'),'B0')
    assert not row['success'] and row['runtime_failed']
    assert row['termination_reason'].startswith('benchmark_error:')


def test_fixed_task_inventory_and_variants():
    tasks=load_tasks()
    assert len(tasks)==24 and len({t['task_id'] for t in tasks})==24
    assert {t['task_family'] for t in tasks}=={f'T{i}' for i in range(1,13)}


def test_c1_preserves_action_interface_failure_limitation():
    row,_=run_trial(task('T11'),'C1-full')
    assert row['runtime_failed'] and row['successful_recoveries']==0
    assert row['actions_taken']==1 and not row['success']


def test_environmental_refresh_updates_recalled_token():
    row,b=run_trial(task('T8'),'C1-full')
    assert row['memory_hits']==1 and row['memory_errors']==0
    assert b['actions'][-1]['argument']=='token:A-new'


def test_zero_resource_denominator_is_null():
    row,_=run_trial(task('T1'),'B0')
    assert summarize([row])['conditions']['B0']['success_per_resource']['actions_taken'] is None


def test_raw_hash_verifier_detects_tampering(tmp_path):
    from hashlib import sha256
    from benchmarks.runner.__main__ import verify_raw
    row,b=run_trial(task('T1'),'B0')
    trace=tmp_path/row['trace_file'];trace.parent.mkdir();trace.write_text(canonical(b))
    (tmp_path/'results.jsonl').write_text(canonical(row))
    manifest=dict(trials=1,files={str(p.relative_to(tmp_path)):sha256(p.read_bytes()).hexdigest() for p in tmp_path.rglob('*') if p.is_file()})
    (tmp_path/'manifest.json').write_text(canonical(manifest))
    assert verify_raw(tmp_path)==manifest
    trace.write_text('{}')
    with pytest.raises(ValueError,match='differs'):
        verify_raw(tmp_path)


def test_resource_cap_excess_is_failure(monkeypatch):
    def overrun(*args,**kwargs):
        b=new_behavior();b['resources']['model_calls']=BUDGET['model_calls']+1
        b['abstentions']=[1]
        return b
    monkeypatch.setattr(baselines,'execute',overrun)
    row,_=run_trial(task('T1'),'B0')
    assert not row['success'] and row['termination_reason']=='resource_limit_exceeded'


def test_infrastructure_failure_marks_incomplete_resource_accounting(monkeypatch):
    def broken(*args,**kwargs): raise RuntimeError('pilot infrastructure error')
    monkeypatch.setattr(baselines,'execute',broken)
    row,_=run_trial(task('T1'),'B1')
    assert row['resource_accounting_complete'] is False
    assert all(v is None for v in summarize([row])['conditions']['B1']['success_per_resource'].values())


def test_freeze_lock_detects_definition_changes(tmp_path):
    from hashlib import sha256
    from benchmarks.runner.__main__ import verify_lock
    definition=tmp_path/'definition.txt';definition.write_text('frozen')
    lock=tmp_path/'experiments/E001_deterministic_baseline/config/protocol-lock.json'
    lock.parent.mkdir(parents=True)
    lock.write_text(canonical(dict(files={'definition.txt':sha256(definition.read_bytes()).hexdigest()})))
    assert len(verify_lock(tmp_path))==64
    definition.write_text('changed')
    with pytest.raises(ValueError,match='Frozen definition changed'):
        verify_lock(tmp_path)


def test_no_memory_adapter_context_hides_historical_records():
    from cafh.adapters.mock import MockAdapter,MockEnvironment
    from cafh.runtime.engine import Engine,RuntimeConfig
    e=Engine(MockAdapter(),MockEnvironment(),objective='Retain immutable goal',
             config=RuntimeConfig(allowed_actions=('echo',),enable_memory_continuity=False))
    e.run_cycle('private first-cycle content')
    context=e._model_context()
    assert 'private first-cycle content' not in canonical(context)
    assert 'echo: actual' not in canonical(context)
    assert e.state['observed_consequences']  # audit retained, not model continuity
    assert context['objective']['statement']=='Retain immutable goal'


def test_experiment_config_matches_executable_definitions():
    from benchmarks.conditions.cafh_condition import ABLATIONS,BLOCKED
    cfg=json.loads((ROOT/'experiments/E001_deterministic_baseline/config/experiment.json').read_text())
    assert cfg['conditions']==list(CONDITIONS)
    assert cfg['budget']==BUDGET
    assert cfg['ablations']==ABLATIONS and cfg['blocked_ablations']==BLOCKED
    assert cfg['tasks']==len(load_tasks()) and cfg['trials']==len(load_tasks())*len(CONDITIONS)
