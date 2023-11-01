#Used to resize images to 300x300. Make sure image is .png before converting, images should be in folder to_300x300

import os
from PIL import Image

def convert_size(folder_dir, new_res):
    for image in os.listdir(folder_dir):
        img_dir = folder_dir + f"\\{image}"
        logo = Image.open(img_dir)
        logo_width = logo.width
        logo_height = logo.height

        #Changing res of all images above 300x300 to 300x300
        if int(logo_width) * int(logo_height) > 90000:
            screenshot_resized = logo.resize(new_res, Image.NEAREST)
            screenshot_resized.save(img_dir, quality=100)


folder_dir = r"/to_300x300"
new_res = (300,300)

convert_size(folder_dir, new_res)