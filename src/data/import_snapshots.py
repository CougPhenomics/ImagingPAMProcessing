# -*- coding: utf-8 -*-
import os
import glob
import re as re
from datetime import datetime, timedelta
import pandas as pd
from src.data import Multi2Singleframes

def import_snapshots(snapshotdir, camera='vis'):
    '''
    Input:
    snapshotdir = directory of .tif files
    camera = the camera which captured the images. 'vis' or 'psii'

    Export multiframe .tif into snapshotdir using format {treatment}-{yyyymmdd}-{sampleid}.tif
    '''

    # %% Get metadata from .tifs
    # snapshotdir = 'data/raw_snapshots/psII'
    framedir = os.path.join(snapshotdir, 'pimframes')
    os.makedirs(framedir, exist_ok=True)
    # first find the multiframe .tif exports from the pim files
    fns = [fn for fn in glob.glob(pathname=os.path.join(snapshotdir,'raw_multiframe','*.tif'))]
    for fn in fns:
        Multi2Singleframes.extract_frames(fn,framedir)

    # now find the individual frame files
    fns = []
    for fname in os.listdir(framedir):
        if re.search(r"-[0-9]+.tif", fname):
            fns.append(fname)

    flist = list()
    fn=fns[0]
    for fn in fns:
        f=re.split('[-]', os.path.splitext(os.path.basename(fn))[0])
        f.append(os.path.join(framedir,fn))
        flist.append(f)

    fdf=pd.DataFrame(flist,columns=['treatment','date','sampleid','imageid','filename'])

    # convert date and time columns to datetime format
    fdf['date'] = pd.to_datetime(fdf.loc[:,'date'])
    fdf['jobdate'] = fdf['date'] #my scripts use job date so id suggest leaving this. i needed to unify my dates when i image overnigh

    # convert image id from string to integer that can be sorted numerically
    fdf['imageid'] = fdf.imageid.astype('uint8')
    fdf = fdf.sort_values(['treatment','date','sampleid'])
    fdf = fdf.set_index(['treatment','date','jobdate'])
    # check for duplicate jobs of the same sample on the same day.  if jobs_removed.csv isnt blank then you shyould investigate!
    #dups = fdf.reset_index('datetime',drop=False).set_index(['imageid'],append=True).index.duplicated(keep='first')
    #dups_to_remove = fdf[dups].drop(columns=['imageid','filename']).reset_index().drop_duplicates()
    #dups_to_remove.to_csv('jobs_removed.csv',sep='\t')
    #

    return fdf
