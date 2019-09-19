from PIL import Image
from PIL import ImageSequence
import sys
import os

def extract_frames(infile,outdir):
    '''
    input:  infile - a multiframe image file
            outdir - the directory to save each of the frames of the image file
    output: the side effect of running this function will be new files using the basename from infile appended with the frame id (1, 2, 3,...).

    Note: you can use . to save to the same directory or .. to save to a directory up one level. Otherwise outdir should be absolute or relative to your working directory.
    '''

    bn = os.path.splitext(os.path.basename(infile))[0]

    im = Image.open(infile)
    index = 1
    for frame in ImageSequence.Iterator(im):
        frame.save(os.path.join(outdir,"%s-%d.tif" % (bn,index)))
        index += 1

if __name__ == "__main__":
    extract_frames(sys.argv[1],sys.argv[2])
