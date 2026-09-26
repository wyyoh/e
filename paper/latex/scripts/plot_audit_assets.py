#!/usr/bin/env python3
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parents[1]
rows=json.loads((P/'figdata/audit_repair/q1_safe_payload_vs_reserve.json').read_text())
plt.rcParams.update({'font.family':['Noto Sans CJK JP','DejaVu Sans'],'font.size':10,'axes.unicode_minus':False,'pdf.fonttype':3,'ps.fonttype':3})
fig,ax=plt.subplots(figsize=(6.4,3.9));palette={'A':'#2F5D8A','B':'#E6A23C','C':'#54B8A9'}
for g in 'ABC':
 r=sorted([r for r in rows if r['service_area']=='S008' and r['aircraft_type']==g],key=lambda r:r['alpha'])
 ax.plot([100*x['alpha'] for x in r],[np.nan if x['safe_payload_kg'] is None else x['safe_payload_kg'] for x in r],color=palette[g],lw=1.6,label=g+'型')
c=35.267806887191433
ax.axhline(14,c='#404955',ls='--',lw=1,label='不可拆饮用水箱：14 kg');ax.axvline(20,c='#707070',ls=':',lw=1);ax.axvline(c,c='#D97C6C',ls='--',lw=1)
ax.annotate('单箱可行性的临界余量\n35.267807%',xy=(c,14),xytext=(20.5,40),arrowprops={'arrowstyle':'->','linewidth':.9,'color':'#D97C6C'},fontsize=9,color='#7A3D36')
ax.text(20.5,77,'基准20%',fontsize=9,color='#505050')
ax.set(xlim=(0,40),ylim=(0,84),xlabel='返航安全余量 α / %',ylabel='S008单点往返最大安全载荷 / kg');ax.grid(c='#E6E6E6',lw=.5);ax.set_axisbelow(True);ax.legend(loc='upper right',fontsize=8.5);fig.tight_layout()
for ext in ['pdf','svg','png']:fig.savefig(P/('figures_generated/q1_payload_response_S008.'+ext),dpi=350,bbox_inches='tight')
plt.close(fig)
