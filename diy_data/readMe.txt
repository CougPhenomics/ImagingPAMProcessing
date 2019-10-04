./readMe.txt
    1. this file describing the contents of this data folder. 
    2. This dataset accompanies the manuscript entitled "Dynamic light experiments and semi-automated phenotyping enabled by self-built plant growth racks and simple upgrades to the Imaging-PAM"
    3. see www.github.com/CougPhenomics/ImagingPAMProcessing for full analysis code

./raw_multiframe
    1. Daily .pim files output from the Imaging-PAM with a corresponding .tif file that was exported using ImagingWin
    2. filename format is <treatment>-<YYYYMMDD>-<sampleid>

./pimframes
    1. Each frame of each .tif file in ./raw_multiframe is extracted to a separate file, using suffix frame #
    2. this folder and these files would be created automatically by scripts/ProcessImages.py

./rgb
    1. images taken with a cellphone in true-color at the end of the experiment

./genotype_map.csv
    1. a mandatory metadata file for analysis that describes the genotype of each plant.
    2. required column headers are treatment,sampleid,roi,gtype

./LemnaTec2.prg
    1. a custom Walz ImagingWin script that replicates the timing protocol in the default Induction Curve tab
    2. light intensities are specific to each camera installation

./pimframes_map.csv
    1. a mandatory metadata file for analysis that describes each frame in the pim/tiff files
    2. required column headers are imageid,frame,parameter

