from cache import *
from prefetcher_info import *
import math
import settings as st
# cache 를 만들고 n개의 line 을 불러오기. 일단은 4개. 이 사이즈를 키우면서 변화 관찰 


class NonePrefetcher:
    # stream buffer 를 여기에서 가지고 있도록 설계해야 할 것 같음. 
    # miss 인지 prefetch hit 인지 알려주는 것 필요. 
    # 이건 근데 LRUCache 에서 처리해야 하겠네. 
    def __init__(self, n = 3): # next 3 lines = 4 lines in total
        self.code = NONE
        
        # granularity 는 어차피 cache 계층에서 바이트 단위의 주소를 
        # unit 으로 나누어 들어오기 때문에 lpn 처럼 들어옴. 64바이트이든 아니든. 
        # 따라서 항상 1임. 
        # self.granularity = 1 
        
        self.aggressiveness = n


    def prefetch(self, lpn: int):
        return []


class NLinePrefetcher:
    # stream buffer 를 여기에서 가지고 있도록 설계해야 할 것 같음. 
    # miss 인지 prefetch hit 인지 알려주는 것 필요. 
    # 이건 근데 LRUCache 에서 처리해야 하겠네. 
    def __init__(self, n = 3): # next 3 lines = 4 lines in total
        self.code = NLINE
        self.granularity = 1 # 64bytes
        self.aggressiveness = n
        self.prefetch_offset = 1


    def prefetch(self, lpn: int):
        fetched_data = []
        _lpn = lpn + self.prefetch_offset
        for n in range(1, self.aggressiveness+1):
            fetched_data.append(_lpn)
            _lpn += self.granularity
        return fetched_data


class BestOffsetPrefetcher:
    # RR table entries: 256 (최근에 발생한 요청 담아두는 테이블)
    # Round Max: 100
    # Score Max: 31
    # 하나의 Round 마다 각 offset 들은 한번씩만 테스트 함. 
    # 각 offset 마다 count 가 필요함. 
    # 

    def __init__(self, k = 16):
        self.code = BO
        self.granularity = 1 # 64bytes
        self.scoremax = 31
        self.offset = [ 1,  2,  3,  4,  5,  6,  8,  9, 10, 12,
                       15, 16, 18, 20, 24, 25, 27, 30, 32, 36,
                       40, 45, 48, 50, 54, 60, 64, 72, 75, 80,
                       81, 90, 96,100,108,120,125,128,135,144,
                      150,160,162,180,192,200,216,225,240,243,
                      250,256 ]
        self.score = {}  # 각 offset 이 최근에 나왔는지 카운트하는 딕셔너리
        self.badscore = 1

        self.roundmax = 100

        self.prefetch_offset = 1 # current prefetch offset 
        self.rr = [] # recent request table 
        self.rr_entries = 256

        self.prefetch_on = 1
        self.aggressiveness = 1
        self.reset_phase()

    def reset_phase(self):
        for offset in self.offset:
            self.score[offset] = 0
        
        self.rounds = 0
        self.cursor = 0  # 현재 check 할 offset 의 인덱스 


    # BO 프리페처는 매 메모리 접근 마다 offset 의 발생 유무를 탐색. 
    def learn(self, lpn: int):
        # offset 학습. lpn 로부터 특정 offset 만큼 떨어진 곳에 request 가 발생한 적이 있는지 카운트 
        offset = self.offset[self.cursor]
        self.cursor += 1 

        # increase offset score 
        prev_lpn = lpn - offset 
        if prev_lpn in self.rr:
            self.score[offset] += 1 

        # print(self.score)
        
        if self.score[offset] == self.scoremax:
            self.prefetch_on = 1
            self.prefetch_offset = offset
            # print("prefetch_offset with scoremax: ", self.prefetch_offset)
            # print(self.score)
            self.reset_phase()
        
        # Maintain recent 256 requests in rr table 
        if lpn in self.rr:
            self.rr.remove(lpn)       
        self.rr.append(lpn)

        if len(self.rr) > self.rr_entries:
            self.rr.pop(0)

        # round check

        if self.cursor == len(self.offset):
            self.cursor = 0

            if self.rounds == self.roundmax:
                # score 가장 높은 애 찾기 
                maxscore = 0
                
                for offset in self.score:
                    if maxscore < self.score[offset]:
                        maxoffset = offset
                
                if maxscore > self.badscore:
                    self.prefetch_on = 1
                    self.prefetch_offset = maxoffset
                    print("prefetch_offset with maxscore: ", self.prefetch_offset)
                else:
                    self.prefetch_on = 0

                self.reset_phase()

    def prefetch(self, lpn: int):
        fetched_data = []

        if self.prefetch_on:
            _lpn = lpn + self.prefetch_offset
            for n in range(1, self.aggressiveness+1):
                fetched_data.append(_lpn)
                _lpn += self.granularity

        return fetched_data
    
class LeapPrefetcher:
    def __init__(self):
        self.code = LEAP
        self.lastprefetchamount = 0
        self.lastprefetchhit = 0
        self.maxprefetchamount = 8
        self.hbuffer = [] # trend detect & aggressiveness
        self.splitvalue = 8
        self.maxbuffersize = 32
        self.last_offset = 1
        self.init_amount = 1
        self.prefetch_offset = 1
        self.aggressiveness = 1
        self.granularity = 1
    
    # hbuffer에 기록하는 함수
    def history_insert(self, addr):
        # hbuffer에 이전 기록이 없는 경우, 델타값 0 설정 후 hbuffer에 넣음
        if len(self.hbuffer) == 0:
            self.hbuffer.append([addr, 0])
            return
        # hbuffer에 이전 기록 있는 경우, 직전 주소 꺼낸 후 현재 주소와의 델타값 계산
        prev = self.hbuffer[-1]
        delta = addr - prev[0]
        # 해당 델타값으로 hbuffer에 넣음
        self.hbuffer.append([addr, delta])
        # hbuffer size가 max를 넘은 경우, 가장 오래된 정보 삭제
        if len(self.hbuffer) > self.maxbuffersize :
            del self.hbuffer[0]

    # Trend detect하는 함수
    def find_offset(self):
        wsize = int(len(self.hbuffer) / self.splitvalue)
        delta = 0

        while True:
            iter_idx = len(self.hbuffer) - (wsize+1)

            # boyer-moore algorithm
            candidate = 0
            vote = 0
            iter_idx2 = iter_idx

            while iter_idx2 != len(self.hbuffer)-1:
                if vote == 0:
                    candidate = self.hbuffer[iter_idx2][-1]
                if self.hbuffer[iter_idx2][-1] == candidate:
                    vote+=1
                else:
                    vote-=1
                iter_idx2+=1
            
            count = 0

            while iter_idx != len(self.hbuffer)-1:
                if self.hbuffer[iter_idx][-1] == candidate:
                    count+=1
                iter_idx+=1

            if count > int(wsize / 2) :
                delta = candidate

            wsize = 2*wsize+1

            if delta!=0 or wsize>len(self.hbuffer) or wsize==0:
                self.prefetch_offset = delta
                if self.prefetch_offset == 0:
                    self.prefetch_offset = self.last_offset
                return
            
    def set_aggressiveness(self, pref_hit_count):
        pref_amount = 0
        if pref_hit_count - self.lastprefetchhit == 0:
            pref_amount = self.init_amount
        else:
            # print(pref_hit_count - self.lastprefetchhit + 1)
            pref_amount = 2**(math.ceil(math.log2(pref_hit_count - self.lastprefetchhit + 1)))
        if pref_amount > self.maxprefetchamount:
            pref_amount = self.maxprefetchamount
        if pref_amount < int(self.lastprefetchamount / 2):
            pref_amount = int(self.lastprefetchamount / 2)
        self.lastprefetchhit = pref_hit_count
        self.lastprefetchamount = pref_amount

        self.aggressiveness = pref_amount

    def reset_(self):
        self.lastprefetchamount = 0
        self.lastprefetchhit = 0
        self.hbuffer = []
        self.last_offset = 1
        self.prefetch_offset = 1
        self.aggressiveness = 1

    def prefetch(self, lpn: int):
        fetched_data = []
        _lpn = lpn + self.prefetch_offset
        for n in range(1, self.aggressiveness+1):
            fetched_data.append(_lpn)
            _lpn += self.granularity * self.prefetch_offset
        return fetched_data
    
class LinuxReadAhead:
    def __init__(self, n = 1):
        self.code = RA
        self.aggressiveness = 4
        self.readahead_on = 1
        self.prev_page = -1 # 마지막으로 접근했던 lpn
        self.hit_counter = 0 # hit counter

    def readaheadOff(self):
        self.readahead_on = 0
        self.aggressiveness = 4

    def aggressControl(self, cond: str):
        if cond == "mp": # memory pressure
            if self.aggressiveness >= 6:
                self.aggressiveness -= 2
            else:
                self.aggressiveness = 4
        
        elif cond == "seq": # sequential access
            if self.aggressiveness < 32:
                self.aggressiveness *= 2

    def prefetch(self, lpn: int):
        fetched_data = []

        if self.readahead_on:
            for i in range(1, self.aggressiveness+1):
                fetched_data.append(lpn+i)
        
        return fetched_data
    

class OfflineClusterPrefetcher:
    # RR table entries: 256 (최근에 발생한 요청 담아두는 테이블)
    # Round Max: 100
    # Score Max: 31
    # 하나의 Round 마다 각 offset 들은 한번씩만 테스트 함. 
    # 각 offset 마다 count 가 필요함. 

    def __init__(self, conf: st.Settings):
        self.code = OC
        self.conf = conf 

        self.granularity = 1 # 64bytes
        self.prefetch_offset = 1 # current prefetch offset 

        self.prefetch_on = 1
        self.aggressiveness = 1

        # cluster information 
        self.cmap = {}
        self.cset = {}

    def set_cluster_data(self, cmap, cset):
        self.cmap = cmap
        self.cset = cset

    def prefetch(self, lpn: int):
        # 접근된 데이터가 속한 cluster id 를 찾고, 
        # 그 중에 현재 cache 에 없는 애들을 올려야 함. 
        # cache 에 있는지 없는지는 cache 계층에서 체크. 
        cid = lpn // self.conf.cluster_size
        mapped_cid = self.cmap[cid]
        fetched_data = self.cset[mapped_cid]
        
        # if self.prefetch_on:
        #     _lpn = lpn + self.prefetch_offset
        #     for n in range(1, self.aggressiveness+1):
        #         fetched_data.append(_lpn)
        #         _lpn += self.granularity

        return fetched_data