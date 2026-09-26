#!/usr/bin/env python3
"""Derive reporting summaries from saved experiment outputs, never rerun or invent trials."""
from pathlib import Path
import csv,json,statistics
P=Path(__file__).resolve().parent;R=P/'results'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def csvsave(p,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def main():
    seeds=[]
    for p in sorted((R/'q2_search').glob('seed_*/run.json')):
        d=read(p);m=d['metrics'];v=read(p.parent/'independent_validation.json')
        if v['failed']!=0:raise ValueError('Search output failed independent validation: '+str(p))
        seeds.append({'seed':d['seed'],'makespan_s':m['makespan_s'],'energy_kwh':m['energy_kwh'],'sorties':m['sorties'],'seconds':d['elapsed_s'],'iterations':sum(d['destroy_use'].values()),'zero_tardy':m['weighted_tardiness_s']==0,'validation_failed':v['failed']})
    if len(seeds)!=20 or {r['seed'] for r in seeds}!=set(range(1,21)):
        raise ValueError('Expected all 20 recorded seeds; partial results are not a completed study')
    save(R/'q2_seed_summary.json',seeds);csvsave(R/'q2_seed_summary.csv',seeds)
    energy=[]
    for factor in [1.01,1.02]:
        folder=R/f'q2_search/energy_factor_{factor:.2f}'
        p=read(folder/'independent_perturbed_replay.json');d=read(folder/'run.json');m=p['metrics']
        if not m['zero_tardiness_feasible']:raise ValueError('Perturbed energy witness is not feasible')
        energy.append({'energy_factor':factor,'sorties':d['metrics']['sorties'],**m,'iterations':sum(d['destroy_use'].values())})
    save(R/'q2_energy_alternatives.json',energy);csvsave(R/'q2_energy_alternatives.csv',energy)
    q4=read(R/'q4/time/fresh_exact/summary.json');best=q4['by_group_count']['2']['minimum_configuration']
    other=[r for r in q4['all_partitions'] if len(r['groups'])==2 and r['groups']!=best['groups']]
    dominance=all(all(a<=b for a,b in zip(best['need_vector'],r['need_vector'])) and best['total_need']<r['total_need'] for r in other)
    save(R/'q4_componentwise_dominance.json',{'selected':best['need_vector'],'others':[r['need_vector'] for r in other],'dominates_all_two_group_partitions':dominance,'scope':'any nonnegative inventory with frozen calendar, relations and lex(gap,total_need,CV); proof by monotonicity of positive part and strict total_need superiority'})
    times=[r['makespan_s'] for r in seeds]
    repairs=read(R/'q3_repair_summary.json')
    summary={'scope':'Executed model-based tests; repeated baselines and deterministic scenarios are not independent stochastic samples',
      'counts':{'q1_exact_scenarios':len(read(R/'q1_reoptimization.json')),'q2_fixed_or_time_repair_records':len(read(R/'q2_perturbations.json')),'q2_independent_seeds':len(seeds),'q2_energy_structural_witnesses':len(energy),'q3_fixed_loss_records':len(read(R/'q3_loss_grid.json')),'q3_fixed_delay_records':len(read(R/'q3_delay_grid.json')),'q3_full_validated_time_repairs':len(repairs),'q4_inventory_by_group_count':len(read(R/'q4_inventory_full.json')),'q4_upstream_plan_audits':len(read(R/'q4_all_candidates.json'))},
      'q2_search':{'minimum_s':min(times),'median_s':statistics.median(times),'maximum_s':max(times),'sample_sd_s':statistics.stdev(times),'coefficient_of_variation':statistics.stdev(times)/statistics.mean(times),'iterations_per_seed':150,'known_feasible_common_initial':True},
      'q3_repair_all_pass':len(repairs)==12 and all(r.get('validation_pass',False) for r in repairs),
      'q4_inventory_selection_componentwise_dominance':dominance,
      'q2_global_certificate':'Inherited formal certificate; all historical pricing leaves were not rerun in this study'}
    save(P/'RESULTS_SUMMARY.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
