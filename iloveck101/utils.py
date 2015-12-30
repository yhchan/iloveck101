import os

from PIL import Image
from io import BytesIO


def get_image_info(data):
    """ read image dimension """
    im = Image.open(BytesIO(data))
    return im.format, im.size[0], im.size[1]


def get_pic_base_folder():
    home = os.path.expanduser('~')
    return os.path.join(home, 'Pictures', 'iloveck101')
