#! Rscript
# Command-line script to produce timelapse videos
# Input: 
#   datadir = relative path to data-specific output directory
#   genotype_mamp = relative path to csv containing genotype info
# Example: Rscript --vanilla scripts/makeVideos.R "output/from_diy_data" "diy_data/genotype_map.csv"

# Get command line arguments
args = commandArgs(trailingOnly = T)
# args  = c('output/from_diy_data', 'diy_data')

# test if there are two arguments: if not, return an error
if (length(args)<2) {
  stop('Two arguments must be supplied:\n1. output directory for a dataset\n2. path to genotype_map.csv\nFor Example: Rscript --vanilla makeVideos.R "output/from_diy_data" "diy_data/genotype_map.csv"', call.=T)
}

# function to try to load required makes. if not loadable, install.
load_install = function(pkg){
  if(!require(pkg, character.only = T)){
    install.packages(pkg, character.only =T, repos = 'https://cloud.r-project.org')
    require(pkg, character.only = T)
    }
}

# load all packages
libs = c('magick','tidyverse','lubridate','av')
tmp = sapply(libs, FUN = load_install)


# setup directories
datadir = args[1]
indir = file.path(datadir, 'pseudocolor_images')
outdir = file.path(datadir, 'timelapse')
dir.create(outdir, show = F, rec = T)

# get genotype info
gmap = read_csv(args[2])

# get data processed
output = read_csv(file.path(datadir,'output_psII_level0.csv')) %>% 
  select(treatment, sampleid, roi, gtype)

# filter gmap for available output files
gmap = inner_join(gmap, output) %>% distinct(treatment, sampleid, roi, gtype)

# setup roi positions for genotype labels
nrow = 3
ncol = 3
nroi = nrow*ncol
rownum = floor((seq_len(nroi)-1) / nrow) + 1
colnum = floor((seq_len(nroi)-1) / ncol + 1)
x0 = 95
xoffset = 170
y0 = 45
yoffset = 170
xpos = x0 + (rownum - 1) * xoffset
ypos = y0 + (colnum - 1) * yoffset
coords = crossing(xpos, ypos) %>% arrange(ypos) %>% mutate(roi = seq_len(nroi)-1) %>% inner_join(gmap)

# function to create treatment label
get_treatment <- function(traynum) {
  paste(traynum,
        gmap %>% filter(sampleid == traynum) %>% distinct(treatment))
}

# get dates from filename
get_dates = function(fns) {
  splitlist = stringr::str_split(basename(fns), '[-\\ ]')
  map_chr(splitlist, .f = ~ lubridate::ymd(.x[2]) %>% as.character)
}

# create list of tray pairs for gifs
fluc_ids = unique(gmap %>% filter(treatment != 'control') %>% pull(sampleid))
cntrl_ids = unique(gmap %>% filter(treatment == 'control') %>% pull(sampleid))
l =  cross2(fluc_ids, cntrl_ids)

# test values
# sampleid0 = 'tray2'
# sampleid1 = 'tray5'
# parameter_string = 'FvFm_YII'#'FvFm_YII' #'t300_ALon_YII'
# il = l[[1]]

# define gif making function
arrange_gif = function(il, parameter_string) {
  uil = unlist(il, rec = F)
  sampleid1 = uil[1]
  sampleid0 = uil[2]
  print(paste(sampleid0, sampleid1, sep = ' x '))
  print(parameter_string)
  
  # get images
  fns0 = dir(file.path(indir, sampleid0),
             pattern = parameter_string,
             full.names = T)
  fns1 = dir(file.path(indir, sampleid1),
             pattern = parameter_string,
             full.names = T)
  
  # get dates from filenames
  dtes0 = get_dates(fns0)
  dtes1 = get_dates(fns1)
  
  # filter for common dates
  commondtes <- intersect(dtes0,dtes1)
  elements0 = dtes0 %in% commondtes
  elements1 = dtes1 %in% commondtes
  dtes0 <- dtes0[elements0]
  dtes1 <- dtes1[elements1]
  fns0 <- fns0[elements0]
  fns1 <- fns1[elements1]

  # get genotypes
  g0 = gmap %>% filter(sampleid == sampleid0) %>% pull(gtype)
  g1 = gmap %>% filter(sampleid == sampleid1) %>% pull(gtype)
  # crossing(dtes0,dtes1) #TODO: filter dates and filenames for common dates
  
  stopifnot(all(dtes0 == dtes1))
  
  # read images
  imgs0 = image_read(fns0)
  imgs1 = image_read(fns1)
  
  # annotate with genotype
  imgs0a = image_annotate(
    imgs0,
    get_treatment(sampleid0),
    size = 24,
    font = 'Arial',
    weight = 700,
    gravity = "NorthWest",
    location = geometry_point(30, 20),
    color = "white"
  )
  
  imgs0a = image_annotate(
    imgs0a,
    dtes0,
    size = 24,
    font = 'Arial',
    weight = 700,
    gravity = "NorthWest",
    location = geometry_point(535, 20),
    color = 'white'
  )
  
  coords %>%
    filter(sampleid == sampleid0) %>%
    group_by(xpos, ypos, roi) %>%
    group_walk(
      keep = T,
      .f = function(df, grp) {
        # print(paste('grp:',grp, collapse=','))
        # print(str(df))
        xpos = df$xpos
        ypos = df$ypos
        gtype = df$gtype
        if (toupper(gtype) == 'WT') {
          gstyle = 'Normal'
        } else {
          gstyle = 'Italic'
        }
        # print(gtype)
        
        imgs0a <<-   image_annotate(
          imgs0a,
          gtype,
          font = 'Arial',
          style = gstyle,
          weight = 700,
          size = 24,
          gravity = 'NorthWest',
          location = geometry_point(xpos, ypos),
          color = 'white'
        )
      }
    )
  
  
  imgs1a = image_annotate(
    imgs1,
    get_treatment(sampleid1),
    size = 24,
    font = 'Arial',
    weight = 700,
    gravity = "NorthWest",
    location = geometry_point(30, 20),
    color = "white"
  )
  imgs1a = image_annotate(
    imgs1a,
    dtes1,
    size = 24,
    font = 'Arial',
    weight = 700,
    gravity = "NorthWest",
    location = geometry_point(535, 20),
    color = 'white'
  )
  
  coords %>%
    filter(sampleid == sampleid1) %>%
    group_by(xpos, ypos, roi) %>%
    group_walk(
      keep = T,
      .f = function(df, grp) {
        # print(paste('grp:',grp, collapse=','))
        # print(str(df))
        xpos = df$xpos
        ypos = df$ypos
        gtype = df$gtype
        if (toupper(gtype) == 'WT') {
          gstyle = 'Normal'
        } else {
          gstyle = 'Italic'
        }
        # #
        imgs1a <<-   image_annotate(
          imgs1a,
          gtype,
          font = 'Arial',
          style = gstyle,
          weight = 700,
          size = 24,
          gravity = 'NorthWest',
          location = geometry_point(xpos, ypos),
          color = 'white'
        )
      }
    )
  
  # combine timelapses
  for (i in 1:length(imgs0)) {
    if (i == 1) {
      newgif = image_append(c(imgs0a[i], imgs1a[i]))
      # newgif = image_append(c(newgif,imgstif[i]), stack=T)
    } else {
      combined  <- image_append(c(imgs0a[i], imgs1a[i]))
      # combined = image_append(c(combined,imgstif[i]), stack=T)
      newgif <- c(newgif, combined)
    }
  }
  # newgif
  outfn = paste0(parameter_string, '_', sampleid0, '_x_', sampleid1, '.gif')
  image_write_video(newgif, file.path(outdir, outfn), framerate = 2)
  # image_write_gif(newgif,file.path(outdir, outfn), delay=0.5)
}


for (param in c('FvFm_YII', 't300_ALon_YII', 't300_ALon_NPQ')) {
  walk(l, arrange_gif, param)
}
