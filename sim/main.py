import os 
import numpy as np
import cache as cc
import prefetcher as pf
from prefetcher_info import *
import settings as st
import preprocessor as pp
import sys


PF_NONE = 0
PF_NLINE = 1
PF_BO = 2
PF_LEAP = 3
PF_RA = 4
PF_OC = 5
PF_ALL = 6



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
    elif choice == PF_OC:
        prefetcher = pf.OfflineClusterPrefetcher(conf)
    else:
        print("Wrong choice for prefetcher")
        sys.exit()

    return prefetcher

def _cache_sim(cache):
    # def do_sim(self, _conf):        
        
    for f in cache.conf.files:
        cache.trc_file = f
        # print(f, end=" ")
        
        # figname = odir + f + "_" + str(chunk_size) + "_" + prefix + "_all.eps"
        # virtual and physical memory plotting 
        for trc in cache.conf.trcs:
            filename = cache.conf.dir + f + "_" + str(cache.conf.line_size) + "." + trc
            cache.reset()
            cache.log_filename = cache.conf.rdir + f + str(cache.conf.line_size) + ".log"
            cache.log_file = open(cache.log_filename, 'w')

            # ofilename = cache.conf.dir + f + ".cid"
            ofilename = "./cset_analysis/" + f + ".cid"                
            preprocessor = pp.PreProcessor(cache.conf)
            cache.cmap, cache.cset = preprocessor.preprocess(filename,ofilename)
            if cache.pf.code == OC:
                cache.pf.set_cluster_data(cache.cmap, cache.cset)

            for k in cache.cmap:
                cache.chit_cnt[cache.cmap[k]] = 0
                cache.cmiss_cnt[cache.cmap[k]] = 0
                cache.cpf_hit_cnt[cache.cmap[k]] = 0

            with open(filename, 'r') as df:
                addr = df.readline()
                while addr:
                    cache.access(addr)
                    addr = df.readline()

            cache.log_file.close()

        print(f, end=' ')
        # print(cache.stats(_plot_dist=0))
        # print(cache.stats(_plot_dist=1))

        cache.stats(_plot_dist=1)


def cache_sim():
    if len(sys.argv) > 1:
        choice = int(sys.argv[1])
    else:
        choice = PF_OC
        # choice = PF_NONE
        # choice = PF_LEAP

    print(choice)

    # Cache settings 
    # prefetcher = pf.NLinePrefetcher()f
    # prefetcher = pf.NonePrefetcher()
    # prefetcher = pf.BestOffsetPrefetcher()
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
    # print("Choose: 0: lru_cache / 1: lfu_cache / 2: distance")
    # choice = int(input())
    # prefix = caches[choice]
    # workload_analyze()
    cache_sim()
