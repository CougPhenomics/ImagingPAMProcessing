from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
import matplotlib.font_manager as fm


def add_scalebar(pseudoimg, pixelresolution, barwidth, barlocation='lower center', fontprops=None, scalebar=None):
    if fontprops is None:
        fontprops = fm.FontProperties(family = 'Arial', size=18, weight='bold')

    ax = pseudoimg.gca()
    barwidth = 20  # mm

    if scalebar is None:
        scalebar = AnchoredSizeBar(ax.transData,
                                   barwidth/pixelresolution,  '2 cm', barlocation,
                                   pad=0.5,
                                   sep=5,
                                   color='white',
                                   frameon=False,
                                   size_vertical=barwidth/pixelresolution/30,
                                   fontproperties=fontprops)

    ax.add_artist(scalebar)

    return ax.get_figure()
