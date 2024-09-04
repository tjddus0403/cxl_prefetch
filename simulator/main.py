import os 
import numpy as np
import cache as cc
import prefetcher as pf
from prefetcher_info import *
import settings as st
import sys
import pandas as pd
from ast import literal_eval

PF_NONE = 0
PF_NLINE = 1
PF_BO = 2
PF_LEAP = 3
PF_RA = 4
PF_CLSTM = 5
PF_ONLY = 6
PF_ALL = 7

def str_to_list(strlist):
    return literal_eval(strlist)

def get_pf(choice, conf):

    if choice == PF_NONE:
        prefetcher = pf.NonePrefetcher()
    elif choice == PF_NLINE:
        prefetcher = pf.NLinePrefetcher()
    elif choice == PF_BO:
        prefetcher = pf.BestOffsetPrefetcher()
    elif choice == PF_LEAP:
        prefetcher = pf.LeapPrefetcher()
    elif choice == PF_RA:
        prefetcher = pf.LinuxReadAhead()
    elif choice == PF_CLSTM:
        prefetcher = pf.LeapPrefetcher()
    else:
        print("Wrong choice for prefetcher")
        sys.exit()

    return prefetcher

def _cache_sim(cache):
    choice = int(sys.argv[1])
    
    for f in cache.conf.files:
        cache.trc_file = f
        
        for trc in cache.conf.trcs:
            filename = cache.conf.dir + f + "_" + str(cache.conf.line_size) + "." + trc
            cache.reset()
            for k in cache.cmap:
                cache.chit_cnt[cache.cmap[k]] = 0
                cache.cmiss_cnt[cache.cmap[k]] = 0
                cache.cpf_hit_cnt[cache.cmap[k]] = 0

            # 여기서 clstm 결과 파일 열고, 밑에 access 시에 함께 전달해줘야 할 듯
            if choice == PF_CLSTM or choice == PF_ONLY:
                # clstm_result = pd.read_csv("../clstm/results/2MB/clstm_cstate/mcf_test_result_addr.csv")
                clstm_result = pd.read_csv("../clstm/results/2MB/cstate_only/astar_test_result_addr.csv")
                clstm_result['pred'] = clstm_result['pred'].apply(str_to_list)
            
            with open(filename, 'r') as df:
                addr = df.readline()
                num = 0
                while addr:
                    if choice == PF_CLSTM:
                        cache.access_clstm(addr, clstm_result['pred'][num])
                    else:
                        cache.access(addr)
                    num+=1
                    addr = df.readline()

        print(f, end=' ')

        cache.stats(_plot_dist=1)


def cache_sim():
    if len(sys.argv) > 1:
        choice = int(sys.argv[1])
    else:
        choice = PF_NONE

    print(choice)

    # Cache settings 
    conf = st.Settings()

    unit = 1 << 14  # 16KB page
    # unit = 1 << 6   # 64B line 
    # slots = int(len(footprint)*0.1)  
    # slots = 1 << 10    # 16MB 
    capacity = 1 << 21 # 2MB 
    # slots = 1 << 8    # 2MB / 8 proceses / 256 slots
    # slots = sys.maxsize
    slots = capacity / unit
    print(slots)

    if choice == PF_ALL:
        for c in range(PF_ALL):
            prefetcher = get_pf(c, conf)
            cache = cc.LRUCache(slots, unit, prefetcher, conf)
            _cache_sim(cache)
    else:
        prefetcher = get_pf(choice, conf)
        cache = cc.LRUCache(slots, unit, prefetcher, conf)
        _cache_sim(cache)


    
if __name__ == "__main__":
    cache_sim()
