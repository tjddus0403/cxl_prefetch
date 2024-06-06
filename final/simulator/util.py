import numpy as np

def list_to_file(mylist, fname):
    with open(fname, 'w') as f:
        for item in mylist:
            if type(item) == list:
                for x in item: 
                    f.write(str(x) + ' ')
                f.write('\n')
            else:
                f.write(str(item) + '\n')


def list_to_file_append(mylist, fname):
    with open(fname, 'a') as f:
        for item in mylist:
            if type(item) == list:
                for x in item: 
                    f.write(str(x) + ' ')
                f.write(' ')
            else:
                f.write(str(item) + ' ')
        f.write('\n')
