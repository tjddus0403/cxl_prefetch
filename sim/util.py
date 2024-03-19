import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


def list_to_file_with_title(mylist, title, fname):

    with open(fname, 'w') as f:
        f.write(title + '\n')
        for item in mylist:
            if type(item) == list:
                # f.write(str(item) + '\n')
                for x in item: 
                    f.write(str(x) + ' ')
                f.write('\n')
            else:
                f.write(str(item) + '\n')


def list_to_file(mylist, fname):
    # print("list length =", str(len(mylist)))
    # print(fname)
    with open(fname, 'w') as f:
        for item in mylist:
            if type(item) == list:
                # f.write(str(item) + '\n')
                for x in item: 
                    f.write(str(x) + ' ')
                f.write('\n')
            else:
                f.write(str(item) + '\n')


def list_to_file_append(mylist, fname):
    # print("list length =", str(len(mylist)))
    # print(fname)
    with open(fname, 'a') as f:
        for item in mylist:
            if type(item) == list:
                # f.write(str(item) + '\n')
                for x in item: 
                    f.write(str(x) + ' ')
                f.write(' ')
            else:
                f.write(str(item) + ' ')
        f.write('\n')

def list_from_file(fname, col=0):
    data = []
    with open(fname, 'r') as f:
        line = f.readline().split()
        while line:
            data.append(int(line[col]))
            line = f.readline()
    return data


def plot_cdf(_data:list, _figname, _label="A", _xlabel="X axis", _clear=1):
    data = np.sort(_data)
    cdf = np.cumsum(data) / np.sum(data)

    plt.plot(data, cdf, label=_label)

    # ax = plt.gca()
    # ax.xaxis.set_major_locator(ticker.MultipleLocator(100))
    # xmax = max(_data)
    # stride = xmax // 5
    # xticks = [ i for i in range(0, xmax, stride)]
    # plt.xlim(0, xmax)

    plt.xlabel(_xlabel)
    plt.ylabel('CDF')
    plt.title(_figname)
    plt.legend(loc='lower right')
    # plt.xticks(xticks)
    # plt.show()

    plt.savefig(_figname)
    if _clear:
        plt.cla()

def plot_scattor(_title="scattor", _xdata=[], _ydata=[], _label="data", _marker='X', _ymax='-1', _figname="scattor.png"):
    plt.title(_title)
    # plt.figure(figsize=(15, 7))
    plt.scatter(_xdata, _ydata, label=_label, marker='X', linewidth=1)
    if _ymax >= 0:
        plt.ylim(0, _ymax)
    
    plt.legend()
    # plt.show()
    plt.savefig(_figname)
    plt.cla()