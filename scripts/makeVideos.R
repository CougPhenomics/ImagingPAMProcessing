library(magick)
library(here)
library(tidyverse)

# setup directories
indir = here('output','from_diy_data','pseudocolor_images')
outdir = here('output','from_diy_data','timelapse') 
dir.create(outdir, show=F, rec=T)

# get genotype info
gmap = read_csv(here('diy_data','genotype_map.csv'))

# setup roi positions for genotype labels
roi = unique(gmap$roi)
nroi = max(gmap$roi)
rownum = floor(roi/3)+1
colnum = floor(roi/3+1)
x0 = 90
xoffset = 105
y0 = 25
yoffset = 125
xpos = x0+(rownum-1)*xoffset
ypos = y0+(colnum-1)*yoffset
coords = crossing(xpos,ypos) %>% arrange(ypos) %>% mutate(roi = seq(0,8)) %>% inner_join(gmap) 

# function to create treatment label
get_treatment <- function(traynum){
  paste(traynum, gmap %>% filter(sampleid==traynum) %>% distinct(treatment))
}

# get dates from filename
get_dates = function(fns){
  splitlist = stringr::str_split(basename(fns),'[-\\ ]')
  map_chr(splitlist,.f = ~lubridate::ymd(.x[2]) %>% as.character)  
}

# create list of tray pairs for gifs
fluc_ids = unique(gmap %>% filter(treatment!='control') %>% pull(sampleid))
cntrl_ids = unique(gmap %>% filter(treatment=='control') %>% pull(sampleid))
l =  cross2(fluc_ids, cntrl_ids)

# test values
# sampleid0 = 'tray2'
# sampleid1 = 'tray5'
# parameter_string = 'FvFm_YII'#'FvFm_YII' #'t300_ALon_YII'
# il = l[[1]]

# define gif making function
arrange_gif = function(il, parameter_string){
  
  uil = unlist(il, rec=F)  
  sampleid1=uil[1]
  sampleid0=uil[2]
  print(paste(sampleid0,sampleid1,sep=' x '))
  print(parameter_string)
  
  # get images
  fns0 = dir(file.path(indir,sampleid0), pattern = parameter_string, full.names = T)
  fns1 = dir(file.path(indir,sampleid1), pattern = parameter_string, full.names = T)

  # get dates from filenames
  dtes0 = get_dates(fns0)
  dtes1 = get_dates(fns1)
  
  # get genotypes
  g0 = gmap %>% filter(sampleid == sampleid0) %>% pull(gtype)
  g1 = gmap %>% filter(sampleid == sampleid1) %>% pull(gtype)
  # crossing(dtes0,dtes1) #TODO: filter dates and filenames for common dates
  
  stopifnot(all(dtes0 == dtes1))
  
  # read images
  imgs0 = image_read(fns0)
  imgs1 = image_read(fns1)
  
  # annotate with genotype
  imgs0_c = image_annotate(imgs0,get_treatment(sampleid0),
                           size = 18, 
                           font = 'Arial',
                           weight = 700,
                           gravity = "NorthWest",
                           location = geometry_point(20,260),
                           color = "white")  
  i0 = image_annotate(imgs0_c,dtes0, 
                      size=18, 
                      font = 'Arial',
                      weight = 700,
                      gravity = "NorthWest", 
                      location = geometry_point(20,285), 
                      color='white')
  
  coords %>% 
    filter(sampleid == sampleid0) %>% 
    group_by(xpos,ypos,roi) %>% 
    group_walk(keep =T, .f = function(df,grp){
        # print(paste('grp:',grp, collapse=','))
        # print(str(df))
        xpos = df$xpos
        ypos = df$ypos
        gtype = df$gtype
        if(toupper(gtype) == 'WT'){
          gstyle = 'Normal'
        } else {
          gstyle = 'Italic'
        }
        # print(gtype)
        
        i0 <<-   image_annotate(i0,
                            gtype,
                            font ='Arial',
                            style = gstyle,
                            weight = 700,
                            size=18,
                            gravity='NorthWest',
                            location = geometry_point(xpos,ypos),
                            color='white')
      })
  
  
imgs1_c = image_annotate(imgs1, get_treatment(sampleid1),
                           size = 18, 
                           font = 'Arial',
                           weight = 700,
                          gravity = "NorthWest", 
                           location = geometry_point(20,260),
                           color = "white")
i1 = image_annotate(imgs1_c,
                    dtes1, 
                    size=18, 
                    font = 'Arial',
                    weight = 700,
                    gravity = "NorthWest", 
                    location = geometry_point(20,285),
                    color='white')

coords %>% 
  filter(sampleid == sampleid1) %>% 
  group_by(xpos,ypos,roi) %>% 
  group_walk(keep =T, .f = function(df,grp){
    # print(paste('grp:',grp, collapse=','))
    # print(str(df))
    xpos = df$xpos
    ypos = df$ypos
    gtype = df$gtype
    if(toupper(gtype) == 'WT'){
      gstyle = 'Normal'
    } else {
      gstyle = 'Italic'
    }
    # # 
    i1 <<-   image_annotate(i1,
                            gtype,
                            font = 'Arial',
                            style = gstyle,
                            weight = 700,
                            size=18,
                            gravity='NorthWest',
                            location = geometry_point(xpos,ypos),
                            color='white')
  })

# combine timelapses
  for(i in 1:length(imgs0)){
    if(i == 1){
      newgif = image_append(c(i0[i], i1[i]))
      # newgif = image_append(c(newgif,imgstif[i]), stack=T)
    } else {
      combined  <- image_append(c(i0[i],i1[i]))    
      # combined = image_append(c(combined,imgstif[i]), stack=T)
      newgif <- c(newgif, combined)
    }
  }
  # newgif
  outfn = paste0(parameter_string,'_',sampleid0, '_x_',sampleid1,'.gif')
  image_write_video(newgif,file.path(outdir, outfn), framerate=2)
  # image_write_gif(newgif,file.path(outdir, outfn), delay=0.5)
}


for(param in c('t300_ALon_YII','t300_ALon_NPQ','FvFm_YII')){
walk(l, arrange_gif, param)
}
