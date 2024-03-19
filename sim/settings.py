
line = 1 << 6
page = 1 << 14

class Settings:
    def __init__(self, obj=None):

        if obj is None:
            self.dir = "./traces/"
            self.odir = "./figures/"
            self.rdir = "./result/"
            # self.files = ["bert", "page_rank", "tpcc", "xz", "ycsb"]
            self.files = ["cc_1MB"]
            # self.files = ["bert"]
            # self.files = ["xz", "ycsb"]
            # self.files = ["bert", "page_rank", "tpcc"]

            # self.files = ["bert", "page_rank","ycsb"]
            # self.files = ["ycsb"]
            # self.files = ["bert"]

            # self.files = ["bert"]
            # self.files = ["tpcc"]
            # self.files = ["tmp"]
            # self.files = ["page_rank"]
            self.trcs = ["paddr"]
            # caches = ["lru_stack", "lfu_stack", "distance"]
            self.page_size = (1 << 14) # Page size (16KB)
            self.line_size = (1 << 6) # Line size 
            self.cluster_size = (1 << 10) # 1024 pages 
        else:
            self.dir = obj.dir
            self.odir = obj.odir
            self.rdir = obj.rdir
            self.files = obj.files
            self.trcs = obj.trcs
            # caches = ["lru_stack", "lfu_stack", "distance"]
            self.page_size = obj.page_size
            self.line_size = obj.line_size
            self.cluster_size = obj.cluster_size
    
    # def __init__(self, obj):
    #     self.obj = obj
