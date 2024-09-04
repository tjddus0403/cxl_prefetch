from abc import ABC, abstractmethod
import prefetcher
import settings as st
from prefetcher_info import *
import bitarray

import numpy as np
from bisect import bisect_left
import sys
import util as ut

import copy

class Cache:
    def __init__(self, capacity: int, unit, conf):
        print("cache slots : ", capacity)
        self.slots = capacity
        self.unit = unit # 캐쉬 내 데이터 관리 단위 
        self.hits = 0
        self.refs = 0
        self.log_file = None
        self.cmap = {}
        self.cset = {}
        self.cmiss_cnt = {}
        self.chit_cnt = {}
        self.cpf_hit_cnt = {}

        self.conf = conf
        
        # for clstm_stream
        self.miss_seq = []
        
        # for clstm_cachestate test
        self.prev_miss_cs = []

    @abstractmethod
    def access(self, line):
        pass


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
               
               
    def access_clstm(self, addr, clstm_result): 
        self.refs += 1 
        addr = int(addr)
        is_hit = 0 # miss
        is_pf_hit = 0        
        closest_lpn = -1
        closest_rank = -1
        # code for clstm
        pf_data_num = 0

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
                closest_lpn = prev_lpn
        else:
            if fw_dist < sys.maxsize:
                dist = int(fw_dist)                  
                closest_lpn = next_lpn
        
        # code for clstm
        # 여기서 clstm의 pf_data 가져옴
        # 여기는 clstmK
        if (self.hits + self.pf_hits)/self.refs < 0.8:
            clstm_result = clstm_result[:]
        elif (self.hits + self.pf_hits)/self.refs < 0.9:
            clstm_result = clstm_result[:5]       
        else:
            clstm_result = clstm_result[:1]
        # 여기까지
        for clstm_pd in clstm_result:
            pd = int(clstm_pd)
            if pd not in self.pf_buff and pd not in self.dlist:
                self.pf_buff.append(pd)
                pf_data_num += 1
            if len(self.pf_buff) > self.pf_buff_slots:
                ofname = "./deep_learning_data/" + self.trc_file + ".pol"
                ut.list_to_file_append([self.pf_buff[0]], ofname)
                self.pf_buff.pop(0) # FIFO
            
        # hit 
        if lpn in self.dlist:
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
                # move hit data into cache
                self.pf_buff.remove(lpn)
                self.pf_hits +=1 
                is_pf_hit = 1
                self.pf_hit_distance.append([self.refs, dist])
                if len(self.cmap) > 0:
                    self.cpf_hit_cnt[mapped_cid] += 1        

                if self.pf.code == RA:
                    self.pf.hit_counter += 1
                    # 연속해서 hit 256번 발생했을 때 read-ahead 끔
                    if self.pf.hit_counter == 256:
                        self.pf.readaheadOff()
            # prefetch miss
            else:
                if len(self.cmap) > 0:                
                    self.cmiss_cnt[mapped_cid] += 1


                if self.pf.code == RA:
                    # dlist, pf_buff 모두 miss일 때 hit counter = 0
                    self.pf.hit_counter = 0


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
            for pd in pf_data:
                if pd not in self.pf_buff and pd not in self.dlist:
                    self.pf_buff.append(pd)
                    # code for clstm
                    pf_data_num+=1
                if len(self.pf_buff) > self.pf_buff_slots:
                    ofname = "./deep_learning_data/" + self.trc_file + ".pol"
                    ut.list_to_file_append([self.pf_buff[0]], ofname)
                    self.pf_buff.pop(0) # FIFO

                    # memory pressure 시, read-ahead 크기 조절
                    if self.pf.code == RA:
                        self.pf.aggressControl("mp")            

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
    
    def access(self, addr):
        self.refs += 1 
        addr = int(addr)
        is_hit = 0 # miss
        is_pf_hit = 0        
        closest_lpn = -1
        closest_rank = -1

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
                closest_lpn = prev_lpn
        else:
            if fw_dist < sys.maxsize:
                dist = int(fw_dist)
                closest_lpn = next_lpn
        
        # hit 
        if lpn in self.dlist:
            # # for clstm_stream_vocabset
            # if len(self.miss_seq) == self.slots:
            #         ofname = "./deep_learning_data/" + self.trc_file + ".miss_seq"
            #         self.miss_seq.append(lpn)
            #         ut.list_to_file_append(self.miss_seq, ofname)
            #         self.miss_seq.pop(-1)
            
            # # for clstm vocabset
            # if len(self.dlist) == self.slots:
            #     ofname = "./deep_learning_data/" + self.trc_file + ".cstate"
            #     self.dlist.append(lpn)
            #     ut.list_to_file_append(self.dlist, ofname)
            #     self.dlist.pop(-1)

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
                
                # # for clstm_stream_vocabset
                # if len(self.miss_seq) == self.slots:
                #     ofname = "./deep_learning_data/" + self.trc_file + ".miss_seq"
                #     self.miss_seq.append(lpn)
                #     ut.list_to_file_append(self.miss_seq, ofname)
                #     self.miss_seq.pop(-1)
                
                # # for clstm vocabset
                # if len(self.dlist) == self.slots:
                #     ofname = "./deep_learning_data/" + self.trc_file + ".cstate"
                #     self.dlist.append(lpn)
                #     ut.list_to_file_append(self.dlist, ofname)
                #     self.dlist.pop(-1)
                

                # move hit data into cache
                self.pf_buff.remove(lpn)
                self.pf_hits +=1 
                is_pf_hit = 1
                self.pf_hit_distance.append([self.refs, dist])
                if len(self.cmap) > 0:
                    self.cpf_hit_cnt[mapped_cid] += 1        

                if self.pf.code == RA:
                    self.pf.hit_counter += 1
                    # 연속해서 hit 256번 발생했을 때 read-ahead 끔
                    if self.pf.hit_counter == 256:
                        self.pf.readaheadOff()
            # prefetch miss
            else:
                # # for clstm_stream
                # self.miss_seq.append(lpn)
                # if len(self.miss_seq) == self.slots+1 :
                #     ofname = "./deep_learning_data/" + self.trc_file + ".miss_seq"
                #     ut.list_to_file_append(self.miss_seq, ofname)
                #     self.miss_seq.pop(0)
                    
                # # for clstm vocabset / dataset
                # if len(self.dlist) == self.slots:
                #     ofname = "./deep_learning_data/" + self.trc_file + ".cstate"
                #     self.dlist.append(lpn)
                #     ut.list_to_file_append(self.dlist, ofname)
                #     self.dlist.pop(-1)
                    
                    
                if len(self.cmap) > 0:                
                    self.cmiss_cnt[mapped_cid] += 1


                if self.pf.code == RA:
                    # dlist, pf_buff 모두 miss일 때 hit counter = 0
                    self.pf.hit_counter = 0


            self.miss_lpn.append(lpn)
            closest_rank = self.dlist.index(closest_lpn) if closest_lpn >= 0 else -1
            self.closest_rank.append(closest_rank)

            self.distance.append([self.refs, is_hit, is_pf_hit, dist, lpn, closest_lpn, closest_rank])
            # replacement
            if len(self.dlist) == self.slots:
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
            
            for pd in pf_data:
                if pd not in self.pf_buff and pd not in self.dlist:
                    self.pf_buff.append(pd)
                if len(self.pf_buff) > self.pf_buff_slots:
                    self.pf_buff.pop(0) # FIFO 

                    # memory pressure 시, read-ahead 크기 조절
                    if self.pf.code == RA:
                        self.pf.aggressControl("mp")            

        # Set a bit array for the accessed line 
        pos = (addr % self.unit) // st.line

        if not self.bitmap.get(lpn):
            ba = bitarray.bitarray()
            lines = self.unit // st.line
            for n in range (lines):
                ba.append(False)
            self.bitmap[lpn] = ba

        # print(pos)
        self.bitmap[lpn][pos] = True
        return is_hit


    def stats(self, _plot_accessed_lines=0, _plot_dist=0):
        stat = f"cache_size = {self.slots} pf_buff_size = {self.pf_buff_slots} total_refs = {self.refs} \
hits = {self.hits} pf_hits = {self.pf_hits} hit_ratio = {self.hits/self.refs} hit_ratio_pf = {(self.hits + self.pf_hits)/self.refs}"

        print(stat)

        return None
