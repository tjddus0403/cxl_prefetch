import pandas as pd
import numpy as np
import random
random.seed(1234)

def make_pagetable(unique_vn):
    pn_candidate = random.sample(range(P_PAGE_NUM), len(unique_vn))
    page_table=pd.DataFrame({'vn':list(unique_vn), 'pn':pn_candidate})
    return page_table

def v2p(page_table, va_trace):
    trace_list = []
    trace_df = pd.DataFrame()
    for i, va in enumerate(va_trace):
        vpn = va // PAGE_SIZE
        idx = va % PAGE_SIZE
        ppn = page_table[page_table['vn']==vpn].iloc[0]['pn']
        pa = ppn * PAGE_SIZE + idx
        trace_list.append({'va':va, 'pa':pa})
        # if (i % 1000000 == 0):
    trace_df = pd.DataFrame(trace_list)
    trace_df.to_csv("bfs_MB.csv", index=False)
    return trace_df

va_df = pd.read_csv("./vaddr/pr.vaddr", names=['va'])
va_trace = va_df['va']
va_range = {"min":va_df.min()['va'], "max":va_df.max()['va']}
VIRTUAL_ADDRESS_SPACE_SIZE = va_range['max'] - va_range['min'] + 1
PHYSICAL_ADDRESS_SPACE_SIZE = VIRTUAL_ADDRESS_SPACE_SIZE * 4
PAGE_SIZE = 1 << 20
V_PAGE_NUM = VIRTUAL_ADDRESS_SPACE_SIZE // PAGE_SIZE
P_PAGE_NUM = PHYSICAL_ADDRESS_SPACE_SIZE // PAGE_SIZE

unique_va = list(set(va_trace))
ununique_vn = list(x//PAGE_SIZE for x in unique_va)
unique_vn = set(ununique_vn)

pg_tb = make_pagetable(unique_vn)

v2p_result = v2p(pg_tb, va_trace)

## v2p
v2p_result['pa'].to_csv("./paddr/pr.paddr", index=False)