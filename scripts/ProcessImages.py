'''
This is the primary script to extract phenotypes from a stack of multiimage tif files. See the README for instructions for how to use this script.
'''

# %% Setup
# Import these libraries (make sure they are installed)
from plantcv import plantcv as pcv
import importlib
import os
from datetime import datetime, timedelta
import cv2 as cv2
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import warnings
warnings.filterwarnings("ignore", module="matplotlib")
warnings.filterwarnings("ignore", module='plotnine')

# %% Import functions from src/ directory to get snaphots, create masks, and setup image classification
from src.data import import_snapshots
from src.segmentation import createmasks
from src.util import masked_stats
from src.util import strip_whitespace
from src.viz import add_scalebar, custom_colormaps

# %% Setup the io directories
indir = 'diy_data'
outdir = os.path.join('output', 'from_' + indir)
debugdir = os.path.join('debug', 'from_' + indir)
maskdir = os.path.join(outdir, 'masks')
fluordir = os.path.join(outdir, 'fluorescence')
os.makedirs(outdir, exist_ok=True)
os.makedirs(debugdir, exist_ok=True)
os.makedirs(maskdir, exist_ok=True)
os.makedirs(fluordir, exist_ok=True)

# %% pixel resolution (mm)
# This needs to be measured for the camera and working distance. With an ImagingPAM you could punch a leaf and then relate the number of pixels to the physical dimension.  See scripts/estimate_area_rgb.py for a method of getting pixel dimensions in ImageJ
pixelresolution = 0.35

# %% Import tif file information based on the filenames. If extract_frames=True it will save each frame form the multiframe TIF to a separate file in data/pimframes/ with a numeric suffix
fdf = import_snapshots.import_snapshots(indir, 'psii', extract_frames=True)

# %% Define the frames from the PSII measurements and merge this information with the filename information
pimframes = pd.read_csv(os.path.join(
    indir, 'pimframes_map.csv'), skipinitialspace=True)
pimframes = strip_whitespace.strip_dfwhitespace(pimframes)#this eliminate weird whitespace around any of the character fields
fdf_dark = (pd.merge(fdf.reset_index(),
                     pimframes,
                     on=['imageid'],
                     how='right'))

# %% remove absorptivity measurements (frames 3 and 4) which are blank images in the default protocol
df = (fdf_dark
      .query('~parameter.str.contains("Abs") and ~parameter.str.contains("FRon")', engine='python')
      )

# %% remove the duplicate Fm and Fo frames where frame = Fmp or Fp (frames 5 and 6)
df = df.query(
    '(parameter!="FvFm") or (parameter=="FvFm" and (frame=="Fo" or frame=="Fm") )'
)

# %% Arrange dataframe of metadata so Fv/Fm comes first
param_order = pimframes.parameter.unique()
df['parameter'] = pd.Categorical(df.parameter,
                                 categories=param_order,
                                 ordered=True)


# %% Setup Debug parmaeters
# pcv.params.debug can be 'plot', 'print', or 'None'. 'plot' is useful if you are testing your pipeline over a few samples so you can see each step.
pcv.params.debug = 'plot'  # 'print' #'plot', 'None'
plt.rcParams["figure.figsize"] = (9, 9) #Figures will show 9x9inches which fits my monitor well.
plt.rcParams["font.family"] = "Arial" # All text is Arial

# %% The main analysis function
# I like to reload my mask function to make sure it's the latest if I've been optimizing it
# importlib.reload(createmasks)

# This function takes a dataframe of metadata that was created above. We loop through each pair of images to compute photosynthetic parameters
def image_avg(fundf):
    # Predefine some variables
    global c, h, roi_c, roi_h

    # Get the filename for minimum and maximum fluoresence
    fn_min = fundf.query('frame == "Fo" or frame == "Fp"').filename.values[0]
    fn_max = fundf.query('frame == "Fm" or frame == "Fmp"').filename.values[0]

    # Get the parameter name that links these 2 frames
    param_name = fundf['parameter'].iloc[0]

    # Create a new output filename that combines existing filename with parameter
    outfn = os.path.splitext(os.path.basename(fn_max))[0]
    outfn_split = outfn.split('-')
    basefn = "-".join(outfn_split[0:-1])
    outfn_split[-1] = param_name
    outfn = "-".join(outfn_split)
    print(outfn)

    # Make some directories based on sample id to keep output organized
    sampleid = outfn_split[2]
    fmaxdir = os.path.join(fluordir, sampleid)
    os.makedirs(fmaxdir, exist_ok=True)

    # If debug mode is 'print', create a specific debug dir for each pim file
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

    # We always identify the leaf area using Fm and then apply the mask to subsequent frames in the induction curve for the same day and sample
    if param_name == 'FvFm':
        # create mask
        mask = createmasks.psIImask(img)

        # find objects and setup roi to designate where the plants should be
        c, h = pcv.find_objects(img, mask)
        roi_c, roi_h = pcv.roi.multi(img,
                                     coord=(160, 90),
                                     radius=30,
                                     spacing=(160, 175),
                                     ncols=3,
                                     nrows=3)


        #setup individual roi plant masks
        newmask = np.zeros_like(mask)

        # compute fv/fm and save to file
        Fv, hist_fvfm = pcv.fluor_fvfm(
            fdark=fdark, fmin=imgmin, fmax=img, mask=mask, bins=128)
        YII = np.divide(Fv, img, out=out_flt.copy(),
                        where=np.logical_and(mask > 0, img > 0))
        cv2.imwrite(os.path.join(fmaxdir, outfn + '_fvfm.tif'), YII)

        # NPQ is 0
        NPQ = np.zeros_like(YII)

        # print Fm
        cv2.imwrite(os.path.join(fmaxdir, outfn + '_fmax.tif'), img)
        # NPQ will always be an array of 0s


    else: # compute YII and NPQ if parameter is other than FvFm
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

    # Make as many copies of incoming dataframe as there are ROIs so all results can be saved
    outdf = fundf.copy()
    for i in range(0, len(roi_c)-1):
        outdf = outdf.append(fundf)
    outdf.imageid = outdf.imageid.astype('uint8')

    # Initialize lists to store variables for each ROI and iterate through each plant
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

        # Filter objects based on being in the defined ROI
        # Filter objects based on being in the defined ROI
        roi_obj, hierarchy_obj, submask, obj_area = pcv.roi_objects(
            img,
            roi_contour=rc,
            roi_hierarchy=rh,
            object_contour=c,
            obj_hierarchy=h,
            roi_type='partial')

        if obj_area > 0:
            # Combine multiple plant objects within an roi together
            plant_contour, plant_mask = pcv.object_composition(
                img=img, contours=roi_obj, hierarchy=hierarchy_obj)

            #combine plant masks after roi filter
            if param_name == 'FvFm':
                newmask = pcv.image_add(newmask, plant_mask)

            # Calc mean and std dev of fluoresence, YII, and NPQ and save to list
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

            # Check if plant is compeltely within the frame of the image
            inbounds.append(pcv.within_frame(plant_mask))
            inbounds.append(pcv.within_frame(plant_mask))

            #Compute the plantarea in mm^2
            plantarea.append(obj_area * pixelresolution**2.)
            plantarea.append(obj_area * pixelresolution**2.)

        else:
            print('!!! No plant detected in roi ', str(i))

            frame_avg.append(0)
            frame_avg.append(0)
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

        # end if-else
    # end roi loop

    # save mask of all plants to file after roi filter
    if param_name == 'FvFm':
        pcv.print_image(newmask, os.path.join(maskdir, outfn + '_mask.png'))

    # Output a pseudocolor of NPQ and YII for each induction period for each image
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
    # If you change the output size and resolution you will need to adjust the  timelapse video script
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

    # check YII values for uniqueness between all ROI. nonunique ROI suggests the plants grew into each other and can no longer be reliably separated in image processing.
    # a single value isn't always robust. I think because there ae small independent objects that fall in one roi but not the other that change the object within the roi slightly.
    # also note, I originally designed this for trays of 2 pots. It will not detect if e.g. 2 out of 9 plants grow into each other
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
# end of function!

# %% Setup Debug parameters
#by default params.debug should be 'None' when you are ready to process all your images
pcv.params.debug = 'None'
# if you choose to print debug files to disk then remove the old ones first (if they exist)
if pcv.params.debug == 'print':
    import shutil
    shutil.rmtree(os.path.join(debugdir), ignore_errors=True)

# %% Testing dataframe
# If you need to test new function or threshold values you can subset your dataframe to analyze some images
# Comment df2= if you want to analyze all files!
# df2=df.query('(sampleid == "tray4" and (jobdate == "2019-08-10" or jobdate == "2019-08-01"))')# and (parameter == "t300_ALon" or parameter == "FvFm"))')
# del df2
# fundf = df2
# del fundf
# # # fundf
# # end testing

# %% Process the files
# check for subsetted dataframe
if 'df2' not in globals():
    df2 = df
else:
    print('df2 already exists!')

# Each unique combination of treatment, sampleid, jobdate, parameter should result in exactly 2 rows in the dataframe that correspond to Fo/Fm or F'/Fm'
dfgrps = df2.groupby(['treatment', 'sampleid', 'jobdate', 'parameter'])
grplist = []
for grp, grpdf in dfgrps:
    # print(grp)#'%s ---' % (grp))
    grplist.append(image_avg(grpdf))
df_avg = pd.concat(grplist)


# %% Add genotype information to the processing results
gtypeinfo = pd.read_csv(os.path.join(indir, 'genotype_map.csv'), skipinitialspace=True)
gtypeinfo = strip_whitespace.strip_dfwhitespace(gtypeinfo)  #strip whitespace from any fields. using sep="\s*,\s" in read_csv doesn't work. first header value get messed up
df_avg2 = (pd.merge(df_avg,
                    gtypeinfo,
                    on=['treatment', 'sampleid', 'roi'],
                    how='inner')
           )

# %% Write the tabular results to file!
(df_avg2.sort_values(['treatment', 'date', 'sampleid', 'imageid'])
 .to_csv(os.path.join(outdir, 'output_psII_level0.csv'), na_rep='nan', float_format='%.4f', index=False)
 )
