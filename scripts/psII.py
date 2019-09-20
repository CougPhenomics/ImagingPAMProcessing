# %% Setup
# Export .tif into outdir from LemnaBase using format {0}-{3}-{1}-{6}
from plantcv import plantcv as pcv
import glob
import importlib
import os
import re as re
from collections import defaultdict
from datetime import datetime, timedelta
import cv2 as cv2
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import warnings
warnings.filterwarnings("ignore", module="matplotlib")
warnings.filterwarnings("ignore", module='plotnine')

# %% Import functions to get snaphots, create masks, and setup image classification
from src.data import import_snapshots
from src.segmentation import createmasks
from src.util import masked_stats
from src.viz import add_scalebar, custom_colormaps
# %% io directories
indir = 'diy_data'
outdir = os.path.join('output', 'from_' + indir)
debugdir = os.path.join('debug', 'from_' + indir)
maskdir = os.path.join(outdir, 'masks')
fluordir = os.path.join(outdir, 'fluorescence')
os.makedirs(outdir, exist_ok=True)
os.makedirs(debugdir, exist_ok=True)
os.makedirs(maskdir, exist_ok=True)
os.makedirs(fluordir, exist_ok=True)

# %% pixel pixel_resolution
# mm (this is approx and should only be used for scalebar)
pixelresolution = 0.35

# %% Import tif files
# importlib.reload(import_snapshots)
fdf = import_snapshots.import_snapshots(indir, 'psii')

# %% Define the frames from the PSII measurements
pimframes = pd.read_csv(os.path.join(
    indir, 'pimframes_map.csv'), skipinitialspace=True)
fdf_dark = (pd.merge(fdf.reset_index(),
                     pimframes,
                     on=['imageid'],
                     how='right'))

# %% remove absorptivity measurements which are blank images
# also remove Ft_FRon measurements. THere is no Far Red light.
df = (fdf_dark
      .query('~parameter.str.contains("Abs") and ~parameter.str.contains("FRon")', engine='python')
      )

# %% remove the duplicate Fm and Fo frames where frame = Fmp and Fp from imageid 5,6
df = df.query(
    '(parameter!="FvFm") or (parameter=="FvFm" and (frame=="Fo" or frame=="Fm") )'
)

# %% Setup output
pcv.params.debug = 'plot'  # 'print' #'plot', 'None'
plt.rcParams["figure.figsize"] = (9, 9)
plt.rcParams["font.family"] = "Arial"

# %% image fucntion

importlib.reload(createmasks)
def image_avg(fundf):
    global c, h, roi_c, roi_h

    # fn_min = fundf.filename.iloc[0]
    fn_min = fundf.query('frame == "Fo" or frame == "Fp"').filename.values[0]
    # fn_max = fundf.filename.iloc[1]
    fn_max = fundf.query('frame == "Fm" or frame == "Fmp"').filename.values[0]
    param_name = fundf['parameter'].iloc[0]

    outfn = os.path.splitext(os.path.basename(fn_max))[0]
    outfn_split = outfn.split('-')
    basefn = "-".join(outfn_split[0:-1])
    outfn_split[-1] = param_name
    outfn = "-".join(outfn_split)
    print(outfn)

    sampleid = outfn_split[2]
    fmaxdir = os.path.join(fluordir, sampleid)
    os.makedirs(fmaxdir, exist_ok=True)

    if pcv.params.debug == 'print':
        debug_outdir = os.path.join(debugdir, outfn)
        if not os.path.exists(debug_outdir):
            os.makedirs(debug_outdir)
        pcv.params.debug_outdir = debug_outdir

    # read images and create mask from max fluorescence
    # read image as is. only gray values in PSII images
    imgmin, _, _ = pcv.readimage(fn_min)
    img, _, _ = pcv.readimage(fn_max)
    fdark = np.zeros_like(img)
    out_flt = fdark.astype('float32')  # <- needs to be float32 for imwrite

    if param_name == 'FvFm':
        # create mask
        mask = createmasks.psIImask(img)

        # find objects and setup roi
        c, h = pcv.find_objects(img, mask)
        roi_c, roi_h = pcv.roi.multi(img,
                                     coord=(160, 90),
                                     radius=30,
                                     spacing=(160, 175),
                                     ncols=3,
                                     nrows=3)


        #setup individual roi plant masks
        newmask = np.zeros_like(mask)

        # compute fvfm
        Fv, hist_fvfm = pcv.fluor_fvfm(
            fdark=fdark, fmin=imgmin, fmax=img, mask=mask, bins=128)
        YII = np.divide(Fv, img, out=out_flt.copy(),
                        where=np.logical_and(mask > 0, img > 0))
        cv2.imwrite(os.path.join(fmaxdir, outfn + '_fvfm.tif'), YII)

        NPQ = np.zeros_like(YII)

        # print Fm
        cv2.imwrite(os.path.join(fmaxdir, outfn + '_fmax.tif'), img)
        # NPQ will always be an array of 0s

    else:
        #use cv2 to read image becase pcv.readimage will save as input_image.png overwriting img
        newmask = cv2.imread(os.path.join(
            maskdir, basefn + '-FvFm_mask.png'), -1)

        # compute YII
        Fvp, hist_yii = pcv.fluor_fvfm(
            fdark, fmin=imgmin, fmax=img, mask=newmask, bins=128)
        # make sure to initialize with out=. using where= provides random values at False pixels. you will get a strange result. newmask comes from Fm instead of Fm' so they can be different
        #newmask<0, img>0 = FALSE: not part of plant but fluorescence detected.
        #newmask>0, img<=0 = FALSE: part of plant in Fm but no fluorescence detected <- this is likely the culprit because pcv.apply_mask doesn't always solve issue.
        YII = np.divide(Fvp, img, out=out_flt.copy(),
                        where=np.logical_and(newmask > 0, img > 0))
        cv2.imwrite(os.path.join(fmaxdir, outfn + '_yii.tif'), YII)

        # compute NPQ
        Fm = cv2.imread(os.path.join(fmaxdir, basefn + '-FvFm_fmax.tif'), -1)
        NPQ = np.divide(Fm, img, out=out_flt.copy(),
                        where=np.logical_and(newmask > 0, img > 0))
        NPQ = np.subtract(NPQ, 1, out=out_flt.copy(),
                          where=np.logical_and(NPQ >= 1, newmask > 0))
        cv2.imwrite(os.path.join(fmaxdir, outfn + '_npq.tif'), NPQ)
    # end if-else Fv/Fm

    # Make as many copies of incoming dataframe as there are ROIs
    outdf = fundf.copy()
    for i in range(0, len(roi_c)-1):
        outdf = outdf.append(fundf)
    outdf.imageid = outdf.imageid.astype('uint8')

    # Initialize lists to store variables for each ROI and iterate
    frame_avg = []
    yii_avg = []
    yii_std = []
    npq_avg = []
    npq_std = []
    plantarea = []
    ithroi = []
    inbounds = []
    i = 0
    rc = roi_c[i]
    for i, rc in enumerate(roi_c):
        # Store iteration Number
        ithroi.append(int(i))
        ithroi.append(int(i))  # append twice so each image has a value.
        # extract ith hierarchy
        rh = roi_h[i]

        # Filter objects based on being in the ROI
        try:
            roi_obj, hierarchy_obj, submask, obj_area = pcv.roi_objects(
                img, roi_contour=rc, roi_hierarchy=rh, object_contour=c, obj_hierarchy=h, roi_type='partial')
        except RuntimeError as err:
            print('!!!', err, str(i))

            frame_avg.append(np.nan)
            frame_avg.append(np.nan)
            yii_avg.append(np.nan)
            yii_avg.append(np.nan)
            yii_std.append(np.nan)
            yii_std.append(np.nan)
            npq_avg.append(np.nan)
            npq_avg.append(np.nan)
            npq_std.append(np.nan)
            npq_std.append(np.nan)
            inbounds.append(np.nan)
            inbounds.append(np.nan)
            plantarea.append(0)
            plantarea.append(0)

        else:

            # Combine multiple plant objects within an roi together
            plant_contour, plant_mask = pcv.object_composition(
                img=img, contours=roi_obj, hierarchy=hierarchy_obj)

            #combine plant masks after roi filter
            if param_name == 'FvFm':
                newmask = pcv.image_add(newmask, plant_mask)

            frame_avg.append(masked_stats.mean(imgmin, plant_mask))
            frame_avg.append(masked_stats.mean(img, plant_mask))
            # need double because there are two images per loop
            yii_avg.append(masked_stats.mean(YII, plant_mask))
            yii_avg.append(masked_stats.mean(YII, plant_mask))
            yii_std.append(masked_stats.std(YII, plant_mask))
            yii_std.append(masked_stats.std(YII, plant_mask))
            npq_avg.append(masked_stats.mean(NPQ, plant_mask))
            npq_avg.append(masked_stats.mean(NPQ, plant_mask))
            npq_std.append(masked_stats.std(NPQ, plant_mask))
            npq_std.append(masked_stats.std(NPQ, plant_mask))
            inbounds.append(pcv.within_frame(plant_mask))
            inbounds.append(pcv.within_frame(plant_mask))
            plantarea.append(obj_area * pixelresolution**2.)
            plantarea.append(obj_area * pixelresolution**2.)

        # end try-except-else
    # end roi loop

    # save mask of all plants to file after roi filter
    if param_name == 'FvFm':
        pcv.print_image(newmask, os.path.join(maskdir, outfn + '_mask.png'))

    # save pseudocolor of all plants in image
    # print pseduocolor
    imgdir = os.path.join(outdir, 'pseudocolor_images', sampleid)
    os.makedirs(imgdir, exist_ok=True)
    npq_img = pcv.visualize.pseudocolor(NPQ,
                                        obj=None,
                                        mask=newmask,
                                        cmap='inferno',
                                        axes=False,
                                        min_value=0,
                                        max_value=2.5,
                                        background='black',
                                        obj_padding=0)
    npq_img = add_scalebar.add_scalebar(npq_img,
                                        pixelresolution=pixelresolution,
                                        barwidth=20,
                                        barlocation='lower left')   
    npq_img.set_size_inches(6,6, forward=False)
    npq_img.savefig(os.path.join(imgdir, outfn + '_NPQ.png'),
                    bbox_inches='tight',
                    dpi = 150)
    npq_img.clf()

    yii_img = pcv.visualize.pseudocolor(YII,
                                        obj=None,
                                        mask=newmask,
                                        cmap=custom_colormaps.get_cmap('imagingwin'),
                                        axes=False,
                                        min_value=0,
                                        max_value=1,
                                        background='black',
                                        obj_padding=0)
    yii_img = add_scalebar.add_scalebar(yii_img,
                                        pixelresolution=pixelresolution,
                                        barwidth = 20,
                                        barlocation = 'lower left')
    yii_img.set_size_inches(6,6, forward=False)
    yii_img.savefig(os.path.join(imgdir, outfn + '_YII.png'),
                    bbox_inches='tight',
                    dpi = 150)
    yii_img.clf()

    # check yii values for uniqueness
    # a single value isn't always robust. I think because there ae small independent objects that fall in one roi but not the other that change the object within the roi slightly.
    rounded_avg = [round(n, 3) for n in yii_avg]
    rounded_std = [round(n, 3) for n in yii_std]
    isunique = not (rounded_avg.count(rounded_avg[0]) == len(yii_avg) and
                    rounded_std.count(rounded_std[0]) == len(yii_std))

    # save all values to outgoing dataframe
    outdf['roi'] = ithroi
    outdf['frame_avg'] = frame_avg
    outdf['yii_avg'] = yii_avg
    outdf['npq_avg'] = npq_avg
    outdf['yii_std'] = yii_std
    outdf['npq_std'] = npq_std
    outdf['plantarea'] = plantarea
    outdf['obj_in_frame'] = inbounds
    outdf['unique_roi'] = isunique

    return (outdf)


# %% Setup output
pcv.params.debug = 'None'
# importlib.reload(createmasks)
if pcv.params.debug == 'print':
    import shutil
    shutil.rmtree(os.path.join(debugdir), ignore_errors=True)

# %% Compute image average and std for min/max fluorescence
# must group so there are pair of images Fp and Fmp or Fo and Fm. make sure df was sorted by datetime and imageid at least
df = df.sort_values(['treatment', 'sampleid', 'imageid'])
# this only works if every category is represented in the first day in the dataframe
param_order = df.parameter.unique()
df['parameter'] = pd.Categorical(df.parameter, categories=param_order, ordered=True)

# importlib.reload(add_scalebar)
# # staret testing
# df2=df.query('(sampleid == "tray4" and (jobdate == "2019-08-10" or jobdate == "2019-08-01") and (parameter == "t300_ALon" or parameter == "FvFm"))')
# del df2
# fundf = df2
# del fundf
# # # fundf
# # end testing

# %% groupby loop works better with multiple ROI
# check for subsetted dataframe
if 'df2' not in globals():
    df2 = df
else:
    print('df2 already exists!')

dfgrps = df2.groupby(['treatment', 'sampleid', 'jobdate', 'parameter'])
grplist = []
for grp, grpdf in dfgrps:
    # print(grp)#'%s ---' % (grp))
    grplist.append(image_avg(grpdf))
df_avg = pd.concat(grplist)


# %% Add genotype information
gtypeinfo = pd.read_csv(os.path.join(indir, 'genotype_map.csv'))
df_avg2 = (pd.merge(df_avg,
                    gtypeinfo,
                    on=['treatment', 'sampleid', 'roi'],
                    how='outer')
           )

(df_avg2.sort_values(['treatment', 'date', 'sampleid', 'imageid'])
 .to_csv(os.path.join(outdir, 'output_psII_level0.csv'), na_rep='nan', float_format='%.4f', index=False)
 )
