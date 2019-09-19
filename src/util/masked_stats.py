import numpy as np

def mean(a, m):
    return(np.mean(a[np.where(m > 0)]))

def std(a, m):
    return(np.std(a[np.where(m > 0)]))
