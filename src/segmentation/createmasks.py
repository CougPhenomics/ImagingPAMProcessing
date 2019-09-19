from plantcv import plantcv as pcv
import os
import numpy as np
import cv2 as cv2
from skimage import filters

def psIImask(img, mode='thresh'):
    ''' 
    Input:
    img = greyscale image
    mode = type of thresholding to perform. Currently only 'thresh' is available
    '''

    # pcv.plot_image(img)
    if mode is 'thresh':

        # this entropy based technique seems to work well when algae is present
        algaethresh = filters.threshold_yen(image=img)
        threshy = pcv.threshold.binary(img, algaethresh, 255, 'light')
        # mask = pcv.dilate(threshy, 2, 1)
        mask = pcv.fill(threshy, 150)
        mask = pcv.erode(mask, 2,1)
        mask = pcv.fill(mask, 45)
        # mask = pcv.dilate(mask, 2,1)
        final_mask = mask  # pcv.fill(mask, 270)

    else:
        pcv.fatal_error('mode must be "thresh" (default) or an object of class pd.DataFrame')

    return final_mask
