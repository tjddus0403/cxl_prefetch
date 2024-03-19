import settings as st


class PreProcessor:
    def __init__(self, conf :st.Settings):
        self.conf = conf
        pass

    def preprocess(self, fname, ofname):
        
            cset = {'key': set()}
            cmap = {}
            tmp = set ()

            print(fname + "...")
            print(self.conf.cluster_size)

            # scan cluster id 
            with open(fname, 'r') as f:
                line = f.readline().split()
                while line:
                    
                    lpn = int(line[0].rstrip()) // self.conf.page_size
                    cid = lpn // self.conf.cluster_size
                    # print(cid)
                    tmp.add(cid)
                    line = f.readline().split()
            
            # assign cluster id 
            i=0
            for cid in tmp:
                cmap[cid] = i
                i += 1

            # convert workloads with cluster id 
            with open(ofname, 'w') as wf:
                with open(fname, 'r') as f:
                    line = f.readline().split()
                    while line:
                        lpn = int(line[0].rstrip()) // self.conf.page_size
                        cid = lpn // self.conf.cluster_size
                        
                        mapped_cid = cmap[cid]
                        if mapped_cid in cset:
                            cset[mapped_cid].add(lpn)
                        else:
                            cset[mapped_cid] = {lpn}

                        wf.write(str(mapped_cid) + " " + str(lpn) + '\n')
                        line = f.readline().split()
            return cmap, cset           

            # # print(cmap)
            # ofname = self.conf.dir + wk + ".cset"
            # with open(ofname, 'w') as wf:
            #     wf.write("cid len lpns\n")
            #     for k in cmap:
            #         wf.write(str(k) + " " + str(len(cset[cmap[k]])) + ' ')
            #         for lpn in cset[cmap[k]]:
            #             wf.write(str(lpn) + ' ')
            #         wf.write('\n')

            # print(type(cmap))

    def preprocess_all(self):
        
        # files = ["tmp"]
        for wk in self.conf.files:
        # for wk in files:
            fname = self.conf.dir + wk + "_" + str(self.conf.line_size) + ".paddr"
            ofname = self.conf.dir + wk + ".cid"

            self.preprocess(self, fname, ofname)

            # cset = {'key': set()}
            # cmap = {}
            # tmp = set ()

            # print(fname + "...")
            # print(self.conf.cluster_size)

            # # scan cluster id 
            # with open(fname, 'r') as f:
            #     line = f.readline().split()
            #     while line:
                    
            #         lpn = int(line[0].rstrip()) // self.conf.page_size
            #         cid = lpn // self.conf.cluster_size
            #         # print(cid)
            #         tmp.add(cid)
            #         line = f.readline().split()
            
            # # assign cluster id 
            # i=0
            # for cid in tmp:
            #     cmap[cid] = i
            #     i += 1

            # # convert workloads with cluster id 
            # with open(ofname, 'w') as wf:
            #     with open(fname, 'r') as f:
            #         line = f.readline().split()
            #         while line:
            #             lpn = int(line[0].rstrip()) // self.conf.page_size
            #             cid = lpn // self.conf.cluster_size
                        
            #             mapped_cid = cmap[cid]
            #             if mapped_cid in cset:
            #                 cset[mapped_cid].add(lpn)
            #             else:
            #                 cset[mapped_cid] = {lpn}

            #             wf.write(str(mapped_cid) + '\n')
            #             line = f.readline().split()                

            # # print(cmap)
            # ofname = self.conf.dir + wk + ".cset"
            # with open(ofname, 'w') as wf:
            #     wf.write("cid len lpns\n")
            #     for k in cmap:
            #         wf.write(str(k) + " " + str(len(cset[cmap[k]])) + ' ')
            #         for lpn in cset[cmap[k]]:
            #             wf.write(str(lpn) + ' ')
            #         wf.write('\n')

            # print(type(cmap))


if __name__ == '__main__':
    conf = st.Settings()
    pp = PreProcessor(conf)
    pp.preprocess()

