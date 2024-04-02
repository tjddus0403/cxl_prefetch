from abc import ABC, abstractmethod
import prefetcher
import settings as st
# import circularLinkedList
from prefetcher_info import *
import bitarray

# cdf graph
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# distance calc 
# from sortedcontainers import SortedSet
from bisect import bisect_left
import sys
import util as ut
import preprocessor as pp

import copy

# class CacheStat:
#     def __init__(self, slots, pf_buff_slots, refs, hits, pf_hits):
#         self.slots = slots
#         self.pf_buff_slots = pf_buff_slots
#         self.refs = refs
#         self.hits = hits
#         self.pf_hits = pf_hits
    
#     def __str__(self):
#         stat = f"cache_size = {self.slots} \npf_buff_size = {self.pf_buff_slots}\ntotal_refs = {self.refs}\n\
# hits = {self.hits}\npf_hits = {self.pf_hits}\nhit_ratio = {self.hits/self.refs}\nhit_ratio_pf = {(self.hits + self.pf_hits)/self.refs}"
        
#         stat = f"cache_size = {self.slots} pf_buff_size = {self.pf_buff_slots} total_refs = {self.refs} \
# hits = {self.hits} pf_hits = {self.pf_hits} hit_ratio = {self.hits/self.refs} hit_ratio_pf = {(self.hits + self.pf_hits)/self.refs}"
#         return stat
    
#         # stat = "cache_size = " + self.sz + "pf_buff_size = " + self.pf_buff_sz + "total_refs = " + self.refs + "hits = " + self.hits + "pf_hits = " + self.pf_hits
#         # return stat

class Cache:
    def __init__(self, capacity: int, unit, conf):
        print("cache slots : ", capacity)
        self.slots = capacity
        self.unit = unit # 캐쉬 내 데이터 관리 단위 

        self.hits = 0
        self.refs = 0

        self.log_filename = "./tmp"
        self.log_file = None

        self.cmap = {}
        self.cset = {}
        self.cmiss_cnt = {}
        self.chit_cnt = {}
        self.cpf_hit_cnt = {}

        self.conf = conf

    # def reset(self):
    #     # print("Cache reset .. ")
    #     self.hits = 0
    #     self.refs = 0

    @abstractmethod
    def access(self, line):
        pass

    # def do_sim(self, sequences):
    #     for addr in sequences:
    #         self.access(addr)    


class LRUCache(Cache):
    def __init__(self, capacity: int, unit, pf, conf):
        super().__init__(capacity, unit, conf)

        # cached data 
        self.dlist = []         # LRU list 
        self.sorted_dlist = []  # Sorted List 

        # Prefetch settings 
        self.pf = pf
        self.pf_n = pf.aggressiveness
        self.pf_buff = [] # maintains prefetched data 
        self.pf_buff_slots = int(self.slots * 0.2)
        print("pf_buff slots : ", self.pf_buff_slots)
        # self.pf_buff_slots = 0
        self.pf_hits = 0

        # bitmap
        self.bitmap = {}
        self.touched_list = []

        # distance 
        self.distance = []
        self.pf_hit_distance = []
        self.pf_miss_distance = []
        self.miss_lpn = []
        self.closest_rank = []
        self.miss_closest_rank = []

    def reset(self):
        # print("Cache reset .. ")
        self.hits = 0
        self.refs = 0
        self.dlist.clear()
        self.sorted_dlist.clear()
        self.distance.clear()
        self.pf_hit_distance.clear()
        self.pf_miss_distance.clear()
        self.miss_lpn.clear()
        self.closest_rank.clear()
        self.miss_closest_rank.clear()
        self.chit_cnt.clear()
        self.cmiss_cnt.clear()
        self.cpf_hit_cnt.clear()


        # Prefetch settings 
        self.pf_buff.clear()
        self.pf_hits = 0

        # leap의 경우, 이전 기록을 가지고 있기 때문에 trace가 바뀔때, 초기화 필요
        if self.pf.code == LEAP:
            self.pf.reset_()        

    # def access(self, addr, clstm_result): ## 여기에 인자로 clstm의 결과도 줘야할듯?
    def access(self, addr):
        ## 여기서 먼저 clstm의 결과를 pf_buff & dlist에 적용하고 시작 (clstm = 매 시점 프리페치 수행)
        self.refs += 1 
        addr = int(addr)
        is_hit = 0 # miss
        is_pf_hit = 0        
        closest_lpn = -1
        closest_rank = -1
        # code for clstm
        pf_data_num = 0

        # if(self.refs % 10000 == 0):
        #     print("refs = ", self.refs, "cache_size = ", len(self.dlist), "hits = ", self.hits, "hit_ratio = ", self.hits/self.refs)

        lpn = addr // self.unit
        cid = lpn // self.conf.cluster_size

        if len(self.cmap) > 0:
            mapped_cid = self.cmap[cid]

        # code for best offset prefetcher 
        if self.pf.code == BO:
            self.pf.learn(lpn)

        # code for read-ahead prefetcher 
        if self.pf.code == RA:
            # 저장된 마지막 접근 page가 없을 경우 
            if self.pf.prev_page < 0:
                self.pf.readahead_on = 1
                self.pf.prev_page = lpn # 마지막 접근 page 저장

            # 마지막으로 접근했던 page가 있을 경우
            else:
                # sequential access -> read-ahead on 상태.
                # agressiveness 증가
                # random->sequential인 경우
                # agressiveness 4에서 시작
                if lpn == self.pf.prev_page + 1:
                    if self.pf.readahead_on:
                        self.pf.aggressControl("seq")
                    
                    else:
                        self.pf.readahead_on = 1
                    
                # random access -> read-ahead off
                else:
                    self.pf.readaheadOff()


        # 현재 cache 내에 있는 애들 중에 거리가 가장 짧은 것. 어떻게 찾지? 
        # 1차원이니까 우선 dlist 를 sorted 형태로 유지. 
        # 가장 가까운 애를 찾아서 그 주변으로 search 하면 될 듯. 
        # sorted 상태를 유지하기 위해서는 tree 등의 자료구조 사용. 
        idx = bisect_left(self.sorted_dlist, lpn)
        prev_lpn = self.sorted_dlist[idx-1] if idx > 0 else -1
        next_lpn = self.sorted_dlist[idx] if idx < len(self.sorted_dlist) else -1

        bw_dist = abs(prev_lpn - lpn) if prev_lpn >= 0 else sys.maxsize
        fw_dist = abs(next_lpn - lpn) if next_lpn >= 0 else sys.maxsize
        dist = -1
        
        if bw_dist < fw_dist:
            if bw_dist < sys.maxsize:
                dist = int(bw_dist * -1)
                # self.distance.append(int(bw_dist * -1))
                # self.distance.append(int(bw_dist))
                closest_lpn = prev_lpn
        else:
            if fw_dist < sys.maxsize:
                dist = int(fw_dist)                    
                # self.distance.append(int(fw_dist))
                closest_lpn = next_lpn
        
        # code for clstm
        # # 여기서 clstm의 pf_data 가져옴
        #     # print("clstm_data_num : ", len(clstm_result), "\nclstm_data : ", clstm_result)
        #     for clstm_pd in clstm_result:
        #         # if pd not in self.pf_buff:
        #         pd = int(clstm_pd)
        #         if pd not in self.pf_buff and pd not in self.dlist:
        #             self.pf_buff.append(pd)
        #             pf_data_num += 1
        #         if len(self.pf_buff) > self.pf_buff_slots:
        #             self.pf_buff.pop(0) # FIFO 
            
        # hit 
        if lpn in self.dlist:
            # # hit인 경우, cstate 추출 (hit임을 명시)
            # if len(self.dlist)==self.slots:
            #     ofname = "./deep_learning_data/" + self.trc_file + ".cstate"
            #     cstate_hit = copy.deepcopy(self.dlist)
            #     # cstate_hit.append('hit')
            #     cstate_hit.append(lpn)
            #     ut.list_to_file_append(cstate_hit, ofname)

            # self.ranks.append(self.stack.index(lpn)+1)
            self.dlist.remove(lpn)
            self.dlist.insert(0, lpn) # MRU position: head 
            self.hits +=1 
            is_hit = 1
            if len(self.cmap) > 0:
                self.chit_cnt[mapped_cid] += 1

            # code for read-ahead
            if self.pf.code == RA:
                self.pf.hit_counter += 1
                # 연속해서 hit 256번 발생했을 때 read-ahead 끔
                if self.pf.hit_counter == 256:
                    self.pf.readaheadOff()  
            
            closest_rank = self.dlist.index(closest_lpn) if closest_lpn >= 0 else -1
            self.distance.append([self.refs, is_hit, is_pf_hit, dist, lpn, closest_lpn, closest_rank])
                    
        else: # miss 
            # prefetch hit  
            if lpn in self.pf_buff: 
                # if len(self.dlist)==self.slots:
                #     ofname = "./deep_learning_data/" + self.trc_file + ".cstate"
                #     cstate_pf_hit = copy.deepcopy(self.dlist)
                #     # cstate_pf_hit.append('pf_hit')
                #     cstate_pf_hit.append(lpn)
                #     ut.list_to_file_append(cstate_pf_hit, ofname)

                # move hit data into cache
                self.pf_buff.remove(lpn)
                self.pf_hits +=1 
                is_pf_hit = 1
                self.pf_hit_distance.append([self.refs, dist])
                # self.pf_hit_distance.append(dist)
                if len(self.cmap) > 0:
                    self.cpf_hit_cnt[mapped_cid] += 1        

                if self.pf.code == RA:
                    self.pf.hit_counter += 1
                    # 연속해서 hit 256번 발생했을 때 read-ahead 끔
                    if self.pf.hit_counter == 256:
                        self.pf.readaheadOff()
            # prefetch miss
            else:
                # pf_miss 여기에서 cache state 로그를 남겨야 함. 
                # 최근 history 도 로그를 남기면 좋을텐데. 일단 cache state 로만 해보자. 
                # if len(self.dlist)==self.slots:
                #     ofname = "./deep_learning_data/" + self.trc_file + ".cstate"
                #     cstate_pf_miss = copy.deepcopy(self.dlist)
                #     cstate_pf_miss.append('pf_miss')
                #     # print(cstate_pf_miss)
                #     cstate_pf_miss.append(lpn)
                #     ut.list_to_file_append(cstate_pf_miss, ofname)

                # # 프리페치 미스에 대한 cstate 데이터 얻기 위한 코드 (deep)
                # if len(self.dlist) == self.slots:
                # #     ofname = "./deep_learning_data/" + self.trc_file + ".cstate"
                #     self.dlist.append(lpn)
                # #     ut.list_to_file_append(self.dlist, ofname)
                #     self.dlist.pop(-1)
                    
                
                if len(self.cmap) > 0:                
                    self.cmiss_cnt[mapped_cid] += 1

                # if self.pf.code == LEAP:
                #     self.miss_closest_rank.append([closest_rank, dist, self.pf.prefetch_offset, self.pf.aggressiveness])
                # else:
                #     self.miss_closest_rank.append([closest_rank, dist])

                # self.pf_miss_distance.append([self.refs, dist])

                if self.pf.code == RA:
                    # dlist, pf_buff 모두 miss일 때 hit counter = 0
                    self.pf.hit_counter = 0


            # # 현재 cache 내에 있는 애들 중에 거리가 가장 짧은 것. 어떻게 찾지? plot_
            # # 1차원이니까 우선 dlist 를 sorted 형태로 유지. 
            # # 가장 가까운 애를 찾아서 그 주변으로 search 하면 될 듯. 
            # # sorted 상태를 유지하기 위해서는 tree 등의 자료구조 사용. 
            # idx = bisect_left(self.sorted_dlist, lpn)
            # prev_lpn = self.sorted_dlist[idx-1] if idx > 0 else -1
            # next_lpn = self.sorted_dlist[idx] if idx < len(self.sorted_dlist) else -1


            # bw_dist = abs(prev_lpn - lpn) if prev_lpn >= 0 else sys.maxsize
            # fw_dist = abs(next_lpn - lpn) if next_lpn >= 0 else sys.maxsize
            # dist = -1
            
            # if bw_dist < fw_dist:
            #     if bw_dist < sys.maxsize:
            #         dist = int(bw_dist * -1)
            #         # self.distance.append(int(bw_dist * -1))
            #         # self.distance.append(int(bw_dist))
            #         closest_lpn = prev_lpn
            # else:
            #     if fw_dist < sys.maxsize:
            #         dist = int(fw_dist)                    
            #         # self.distance.append(int(fw_dist))
            #         closest_lpn = next_lpn


            self.miss_lpn.append(lpn)
            closest_rank = self.dlist.index(closest_lpn) if closest_lpn >= 0 else -1
            self.closest_rank.append(closest_rank)

            self.distance.append([self.refs, is_hit, is_pf_hit, dist, lpn, closest_lpn, closest_rank])
            # replacement
            if len(self.dlist) == self.slots:
                # oldest = self.stack.pop(0)
                evicted_lpn = self.dlist.pop(-1)
                self.sorted_dlist.remove(evicted_lpn)
                
                # count the number of accessed lines within page 
                ba = self.bitmap.pop(evicted_lpn)
                accessed_lines = ba.count(True)
                if self.log_file:
                    self.log_file.write(str(accessed_lines) + "\n")
                self.touched_list.append(accessed_lines)

            # insert accessed data into cache 
            self.dlist.insert(0, lpn)

            # insert accessed data into cache set
            assert lpn not in self.sorted_dlist
            idx = bisect_left(self.sorted_dlist, lpn)
            self.sorted_dlist.insert(idx, lpn)

            # prefetch on prefetch hit or demand miss
            # pf_data = self.pf.prefetch(int(lpn), 1) 
            # nline prefetcher 도 offset 안줘도 될듯. 
            # 항상 다음 n개 이므로. 

            if self.pf.code == LEAP:
                self.pf.history_insert(lpn)
                self.pf.find_offset()
                self.pf.set_aggressiveness(self.pf_hits)

            # access pattern 파악 위해서 lpn tracking
            if self.pf.code == RA:
                self.pf.prev_page = lpn

            pf_data = self.pf.prefetch(int(lpn))
            # 여기에서 leap과 clstm의 pf_data 데이터 결합
            # clstm의 pf_data는 문자열임에 주의 (정수형변환 필요)
            # print("pf_data_num : ", len(pf_data), "\npf_data : ", pf_data)
            # print("type :", type(pf_data[0]))
            for pd in pf_data:
                # if pd not in self.pf_buff:
                if pd not in self.pf_buff and pd not in self.dlist:
                    self.pf_buff.append(pd)
                    # code for clstm
                    pf_data_num+=1
                if len(self.pf_buff) > self.pf_buff_slots:
                    self.pf_buff.pop(0) # FIFO 

                    # memory pressure 시, read-ahead 크기 조절
                    if self.pf.code == RA:
                        self.pf.aggressControl("mp")            

            # print(lpn, self.pf_buff)
        # code for clstm
        ofname = "./deep_learning_data/pf_data_num_leap.txt"
        ut.list_to_file_append([pf_data_num], ofname)
        
        # Set a bit array for the accessed line 
        pos = (addr % self.unit) // st.line

        if not self.bitmap.get(lpn):
            ba = bitarray.bitarray()
            lines = self.unit // st.line
            # print(lines)
            for n in range (lines):
                ba.append(False)
            self.bitmap[lpn] = ba

        # print(pos)
        self.bitmap[lpn][pos] = True
        return is_hit


    def stats(self, _plot_accessed_lines=0, _plot_dist=0):
    #     cache_stat = CacheStat(self.slots,
    #                           self.pf_buff_slots,
    #                           self.refs, self.hits, self.pf_hits)
  
        stat = f"cache_size = {self.slots} pf_buff_size = {self.pf_buff_slots} total_refs = {self.refs} \
hits = {self.hits} pf_hits = {self.pf_hits} hit_ratio = {self.hits/self.refs} hit_ratio_pf = {(self.hits + self.pf_hits)/self.refs}"

        print(stat)

        # cset to file 
        ofname = "./cset_analysis/" + self.trc_file + ".cset"

        with open(ofname, 'w') as wf:
            wf.write("mcid ocid len hit pf_hit miss lpns\n")
    
            for k in self.cmap:
                mk = self.cmap[k]
                wf.write(str(mk) + " " + str(k) + " " + str(len(self.cset[mk])) + ' ')
                wf.write(str(self.chit_cnt[mk])+ " " + str(self.cpf_hit_cnt[mk])+ " " +str(self.cmiss_cnt[mk])+ " ")
                for lpn in self.cset[mk]:
                    wf.write(str(lpn) + ' ')
                wf.write('\n')

        # print(type(cmap))

        if _plot_accessed_lines:
            # plot touched lines 
            data = np.sort(self.touched_list)
            cdf = np.cumsum(data) / np.sum(data)
            figname = self.trc_file + ".png"
            plt.plot(data, cdf, label=self.trc_file)

            self.bitmap.clear()
            self.touched_list.clear()

            plt.xlim(0, 256)
            # ax = plt.gca()
            # ax.xaxis.set_major_locator(ticker.MultipleLocator(100))
            xticks = [ i for i in range(0, 256, 16)]

            plt.xlabel('Number of accessed lines')
            plt.ylabel('CDF')
            # plt.title(f)
            plt.legend(loc='lower right')
            plt.xticks(xticks)
            # plt.show()


            plt.savefig(figname)
            plt.cla()

        if _plot_dist:
            dir="./distance_analysis/"
            # figname= dir + self.trc_file + "_miss_distance.png"
            # ut.plot_cdf(self.distance,_figname=figname, _label="miss_dist", _xlabel="distance")
            # filename= dir + self.trc_file + "_miss_distance_all.txt"
            # title = "refs is_hit is_pf_hit dist lpn closest_lpn closest_rank"
            # ut.list_to_file(self.distance, title, filename)
            # ut.list_to_file_with_title(self.distance, title, filename)
            filename= dir + self.trc_file + "_" + self.pf.code + "_pf_hit_distance.txt"          
            print(filename)
            ut.list_to_file(self.pf_hit_distance, filename)

            # filename= dir + self.trc_file + "_" + self.pf.code + "_pf_miss_distance.txt"
            # ut.list_to_file(self.pf_miss_distance, filename)

            # filename= dir + self.trc_file + "_" + self.pf.code + "_miss_lpn.txt"
            # ut.list_to_file(self.miss_lpn, filename)

            # filename= dir + self.trc_file + "_" + self.pf.code + "_closest_rank.txt"
            # ut.list_to_file(self.closest_rank, filename)

            # filename= dir + self.trc_file + "_" + self.pf.code + "_miss_closest_rank.txt"
            # print(filename)
            # ut.list_to_file(self.miss_closest_rank, filename)

            '''
            from scipy.stats import norm
            # normal distribution 
            mean = np.mean(self.distance)
            std = np.std(self.distance)
            rthreshold = mean + 3 * std
            lthreshold = mean - 3 * std

            print(mean, std)

            data = np.array(self.distance)
            # filtered_data = data[data <= rthreshold & data >= lthreshold]

            # x = np.linspace(min(filtered_data), max(filtered_data), 100)
            x = np.linspace(min(self.distance), max(self.distance), 100)
            # x = np.linspace(mean - std, mean + std, 100)
            # x = np.linspace(-10000, 10000, 100
            pdf = norm.pdf(x, mean, std)

            plt.plot(x, pdf)
            # plt.hist(self.distance, bins='auto', density=True, alpha=0.5)
            plt.ylim(0, 0.00001)
            plt.hist(self.distance, bins='auto', density=True, alpha=0.5)
            plt.xlabel('Value')
            plt.ylabel('Density')
            plt.title('Normal Distribution')
            plt.legend(['PDF', 'Histogram'])
            # plt.show()
            figname="dist.png"
            plt.savefig(figname)
            plt.cla()

            '''
            '''
            # histogram 
            width=1
            bins = np.arange(-25, 26, width)
            x = np.arange(-25, 26, width)
            hist, _ = np.histogram(self.distance, bins=bins)

            plt.figure(figsize=(15, 7))
            plt.bar(bins[:-1], hist, align='edge', width=width)
            plt.xticks(x)

            # plt.plot()
            plt.show()
            '''

        return None

        
# class OPTCache(Cache):
#     def __init__(self, capacity: int, unit, pf=None):
#         super().__init__(capacity, unit)

#         # # Prefetch settings 
#         # self.pf = pf
#         # self.pf_n = pf.aggressiveness
#         # self.pf_buff = [] # maintains prefetched data 
#         # self.pf_buff_slots = int(self.slots * 0.2)
#         # self.pf_hits = 0

#         # Workloads 
#         self.sequences

#     def __find_farest(self):
#         return None


#     def access(self, line) -> None:
#         self.refs += 1 
#         line = int(line)

#         # line 을 담고 있는 unit 을 찾아야 함. unit 크기로 나누어 몫만 취하면 됨. 
#         lpn = line // self.unit 

#         if lpn in self.dlist:
#             # self.ranks.append(self.stack.index(lpn)+1)
#             self.dlist.remove(lpn)
#             self.dlist.insert(0, lpn) # MRU position: head 
#             self.hits +=1 

#         else:
#             # search prefetched data buff 
#             if lpn in self.pf_buff: 
#                 # move hit data into cache
#                 self.pf_buff.remove(lpn)
#                 self.pf_hits +=1 
            
#             if len(self.dlist) == self.slots:
#                 # oldest = self.stack.pop(0)
#                 self.dlist.pop(-1)
#             self.dlist.insert(0, lpn)

#             # prefetch on prefetch hit or demand miss
#             pf_data = self.pf.prefetch(int(lpn), 1)

#             for pd in pf_data:
#                 if pd not in self.pf_buff:
#                     self.pf_buff.append(pd)
                
#                 if len(self.pf_buff) > self.pf_buff_slots:
#                     self.pf_buff.pop(0) # FIFO 
            
#             # print(lpn, self.pf_buff)

#     def stats(self):
#         cache_stat = CacheStat(self.slots,
#                               self.pf_buff_slots,
#                               self.refs, self.hits, self.pf_hits)
#         return cache_stat
