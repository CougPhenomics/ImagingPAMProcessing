'''
This file was used to compute area of plants from rgb images from a cell phone. 
We compared this to our results from the PAM camera for a sanity check. 
You will need to use software like ImageJ to identify the pixel resolution if you do not know it. 
We use 2" pots and used the "Set Scale" feature in imageJ ot identify the number of pixels corresponding to 2".
For example: in ImageJ "set scale" 425 pixels across 2" pot = 212 pixel/inch = 0.12 mm/pixel
'''


from plantcv import plantcv as pcv

pcv.params.debug = 'plot'

traynum = 7

if traynum == 2:
    pixelres = 1/226*25.4#.11 #convert from pixels/inch to mm/pixel
elif traynum == 3:
    pixelres = 1/200*25.4#.13
elif traynum == 4:
    pixelres = 1/215*25.4#.12
elif traynum == 5:
    pixelres = 1/213*25.4#0.12
elif traynum == 6:
    pixelres = 1/195*25.4#.13
elif traynum == 7:
    pixelres = 1/202*25.4#.13

img,_,_ = pcv.readimage('diy_data/rgb/tray'+str(traynum)+'.png')
imga = pcv.rgb2gray_lab(img, 'a')
thresh = pcv.threshold.binary(imga,115, 255,'dark')
mask = pcv.fill(bin_img = thresh, size=200)
c_wt, h_wt = pcv.roi.rectangle(img,1200,300,250,800)

id_objects, obj_hierarchy = pcv.find_objects(img,mask)
roi_objects, hierarchy3, kept_mask, obj_area = pcv.roi_objects(img=img, roi_contour=c_wt,
                                                                roi_hierarchy=h_wt,
                                                                object_contour=id_objects,
                                                                obj_hierarchy=obj_hierarchy,
                                                                roi_type='partial')

obj, mask = pcv.object_composition(img=img, contours=roi_objects, hierarchy=hierarchy3)
shape_img = pcv.analyze_object(img=img, obj=obj, mask=mask)

pcv.outputs.observations['area']['value']/2 * pixelres * pixelres
#WT
# tray 2 - 177
# tray 3 - 227
# tray 4 - 198
# tray 5 - 595
# tray 6 - 551
# tray 7 - 421
#stn7
# tray 2 - 164
# tray 3 - 147
# tray 4 - 167
# tray 5 - 354
# tray 6 - 365
# tray 7 - 343