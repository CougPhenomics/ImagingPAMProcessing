# Phenomics Workflow for Processing Images from Walz Imaging-PAM
This directory contains the scripts that accompany the manuscript: 

*Dynamic light experiments and semi-automated phenotyping enabled by self-built plant growth racks and simple upgrades to the Walz Imaging-PAM*

by Dominik Schneider, Laura S. Lopez, Meng Li, Joseph D. Crawford, David M. Savage, and Hans-Henning Kunz

DOI: ###

These scripts can be used to efficiently process sets of image files from a Walz Imaging-PAM that have been setup in line with the recommendations in our manuscript.

## Setup

The workflow in this repository uses both Python and R and assumes you are familiar enough with these to use them. In general though, there is very little code you should need to modify.

The quickest way to install Python and PlantCV is with [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (a lightweight version of Anaconda). To recreate the exact environment with which this repository was developed, download and install Miniconda. Also, download this repository as a .zip file (see green "Clone or download" button) and extract it to your computer. Using a Terminal (MacOS, Linux) or the Anaconda Prompt (Windows), change directory to the repository directory you extracted that contains `environment_manuscript.yml` and use the command `conda env create -f environment_manuscript.yml` to install all necessary packages. More generally, you should be able to use `conda env create -f environment_current.yml` to install the most current versions of these libraries (including PlantCV). To activate the environment, use for example `conda activate plantcv_current` where `plantcv_current` is the name of your environment.

You may also find the installation instructions helpful in the [PlantCV documentation](https://plantcv.readthedocs.io/en/stable/installation/#install-via-a-package-manager). 

To install R, download [R from CRAN](https://www.r-project.org/) and then install [RStudio](https://www.rstudio.com/) to make it easier to work with R scripts. You will also need to install additional libraries using `install.packages(c('tidyverse','here','magick','tidylog','cowplot','scico','RColorBrewer','bookdown','av'))`. If something doesn't work please install the requested packages, but the specific package versions used in development can be found in [`RsessionInfo.txt`](RsessionInfo.txt).

If you have not done so already, download this repository as a .zip file (see green "Clone or download" button) and extract it to your computer.

### Organize Image files
You need to export your .pim files to multiframe .tifs, either using the ImagingWin dialog (Export button lower left, then select .tif) or as the final step in your custom Walz script, and then drop them in `diy_data/raw_multiframe`. We suggest setting up a new data directory for your own project, in which case you would have `new_data/raw_multiframe`.

Each tif file should be labeled with exactly 2 dashes, 2 descriptors, and a date: e.g. control-20190501-tray2.tif. It is assumed the first descriptor is the treatment, the second descriptor is a sample ID number, and the date is in the format YYYYMMDD.

### Document the Metadata

Additionally you will need `pimframes_map.csv` to describe each frame and `genotype_map.csv` to describe the genotype of each plant. It is important that metadata of your filename descriptors and your images match.

The contents of `diy_data/pimframes.csv` should have 3 column headers EXACTLY as specified in the example file. The `imageid` is an identifier for each frame of each pim file that is appended to the end of the filename when the multiframe tif is converted to singleframe tifs. `frame` defines the frame and the order is standard for a .pim file (e.g. Fp = F', Fmp = Fm'). `parameter` is used to link the two frames as a single photosynthetic measurement:

```
imageid,frame,parameter
1,Fo,FvFm
2,Fm,FvFm
3,AbsR,AbsR
4,AbsN,AbsN
5,Fp,FvFm
6,Fmp,FvFm
7,Fp,t40_ALon
8,Fmp,t40_ALon
9,Fp,t60_ALon
10,Fmp,t60_Alon
...
etc
...
```

The contents of `diy_data/genotype_map.csv` should have 3 column headers EXACTLY as specified in the example file. If you are following the methods in our manuscript then you will have the numbers 0 through 8 as your roi numbers (for a 3x3 grid of plants). Make sure to identify your own genotypes for each plant in the last column:

```
treatment, sampleid, roi, gtype
control, tray2, 0, wt
control, tray2, 1, stn7
control, tray2, 2, stn7
control, tray2, 3, wt
...
etc
...

```

See `diy_data/` for the dataset used in the manuscript.

## Run the Image Processing

At the very least, you will need need to modify [`scripts/ProcessImages.py`](scripts/ProcessImages.py) in 1 place:
1. you must change `indir` to point to your data directory.

Three other modifications may be necessary to work well with other data:

1. It is also likely you will need to modify the location of the ROI to indicate where the plants are in the image. Even if you are using the 9 plant arrangement using the sample crate and 9 pot holders described in the text, it is likely your working distance will be slightly different and therefore your plant positions will be different relative to the image frame. In this case you must change the location of your ROI's as prescibed with `pcv.roi.multi()` in `scripts/ProcessImages`. See [plantcv documentation](https://plantcv.readthedocs.io/en/stable/roi_multi/) for details. You can test your ROI arrangement by stepping through the analysis with a single image.

2. You many also need to adjust the image segmentation function `psIImask` in `src/segmentatoin/createmasks.py`. Image segmentation is generally quite specific to the imaging conditions. An automated estimate for the initial threshold value is provided based on Yen’s Algorithm (Yen et al. 1995), which is an entropy-based method implemented in the Python package scikit-image (Walt et al. 2014). This is followed by cleaning steps to remove small noise in the mask. In particular, we expect the cleaning steps may need to be modified to adapt to unique imaging conditions from individual Imaging-PAM setups. It should be noted that severe algae growth will contaminate the images and make the image segmentation difficult. For more guidance on image segmentation we refer the reader to the excellent tutorials hosted by PlantCV (https://plantcv.readthedocs.io).

3. The python script outputs plant area that is automatically determined from the object detection algorithm implemented through PlantCV. It is important that each user update the `pixel_resolution` variable for their own setup to accurately convert pixels to mm^2. This variable will be specific to the camera and working distance and can be found near the top of the main python script. This need only be performed once if the camera settings remain constant. We recommend imaging a plant with a hole punch of a known size and then measuring the width in pixels of the hole using ImageJ. Pixel_resolution is then calculated as diameter in mm of holepunch divided by diameter in pixels of holepunch. 

To run the pipeline, make sure your plantcv python environment is in your path. You may need to run the command `conda activate plantcv` in your Terminal or Anacona Prompt window. Also, open the project directory with `cd` (this repository that you extracted from the zip) in the Terminal or Anaconda Prompt window that includes your conda environment (note the (plantcv) on the left). Then use ipython to run the script:

```
(plantcv) ~/Documents/phenomics> cd <project directory>
(plantcv) ~/Documents/phenomics/DIY> ipython scripts/ProcessImages.py
```

## Confirming Image Segmentation

The script provided does some automatic image segmentation to identify the plant area in the images. *It is important that you confirm the masks are reasonably accurate*. Running the analysis will create mask files for each sample in `output/from_diy_data/masks` so you can determine if plants were correctly identified. You may need to change the masking procedure if your lighting conditions are substantially different than ours or if you get a lot of algae growth. To do so you will need to change the function `psIImask()` in `src/segmentation/create_masks.py`. Please see the tutorials in the [plantcv documentation](https://plantcv.readthedocs.io/en/stable/psII_tutorial/) for more guidance.

## Visualizing the Extracted Phenotypes

Visualization is mostly done in R. Please install R and RStudio. Open the RStudio project by double click the DIY.Rproj or selecting DIY.Rproj from within RStudio with "Open project..."

1. Timelapse Videos!
   
   By default, pseudocolor_images are saved to `output/from_diy_data/pseudocolor_images` for *Fv/Fm*, and YII and NPQ at each time step of the induction curves. An R script `scripts/makeVideos.R` will assemble these pseudocolor images into gifs of pairs of trays. Make sure you install the libraries listed at the top of the script. Do not forget to customize the data directory path specific to your experiment. After you run the script the videos can be found in `output/from_diy_data/timelapse`.

2. Timeseries and Deviation Plots!
    
    Additionally, we developed an Rmarkdown report that can generate timeseries plots and deviation plots to visualize the treatment effect and difference from WT. These plots are designed to help you quickly identify anomalous data, either due to bad processing or an exciting new phenotype! Figure 6 from the paper is a compilation of a subset of these figures and saved to `output/from_diy_data/figs`. To generate the report, open `reports/postprocessingQC.Rmd` and "Knit" the report. An html file should appear next to the .Rmd file with all the figures.

