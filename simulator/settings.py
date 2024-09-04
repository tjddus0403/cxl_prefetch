
line = 1 << 6
page = 1 << 14

class Settings:
    def __init__(self, obj=None):

        if obj is None:
            self.dir = "./traces/paddr/2MB/astar/"
            # self.files = ["mcf_5m"]
            self.files = ["astar_1m_tail"]
            # self.files = ["mcf_4m"]
            # self.files = ["mcf_3m"]

            self.trcs = ["paddr"]
            
            self.page_size = (1 << 14) # Page size (16KB)
            self.line_size = (1 << 6) # Line size 
            self.cluster_size = (1 << 10) # 1024 pages 
        else:
            self.dir = obj.dir
            self.files = obj.files
            self.trcs = obj.trcs
            
            self.page_size = obj.page_size
            self.line_size = obj.line_size
            self.cluster_size = obj.cluster_size