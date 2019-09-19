'''
This file can be used to design your own colormap and plot it next to another colormap. it was originally used to replicated the ImagingWin colormap, which is based on hsv.

'''

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
import numpy.random as random

hsv = cm.get_cmap('hsv', 256)
newcolors = hsv(np.linspace(0, 1, 256))
keep = newcolors[5:-25,:]
newcolors = np.vstack((keep[:10,:],keep))
black = np.array([0, 0, 0, 1])
newcolors[:10,:] = black
newcmp = ListedColormap(newcolors)


def plot_examples(cms):
    """
    helper function to plot two colormaps
    """
    data = np.random.random_sample((30, 30))
    
    fig, axs = plt.subplots(1, 2, figsize=(26, 8), constrained_layout=True)
    for [ax, cmap] in zip(axs, cms):
        psm = ax.pcolormesh(data, cmap=cmap, rasterized=True, vmin=0, vmax=1)
        fig.colorbar(psm, ax=ax, orientation='horizontal')
    plt.show()

plot_examples([hsv, newcmp])# -*- coding: utf-8 -*-

