import struct

from PIL import Image
from io import BytesIO

import requests
from lxml import etree

from .exceptions import URLParseError


def get_image_info(data):
    """
    read image dimension
    """
    im = Image.open(BytesIO(data))
    return im.format, im.size[0], im.size[1]

def parse_url(url):
    """
    parse image_url from given url
    """

    REQUEST_HEADERS = {
        'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.57 Safari/537.36'
    }

    # fetch html and find images
    title = None
    for attemp in range(3):
        resp = requests.get(url, headers=REQUEST_HEADERS)
        if resp.status_code != 200:
            print('Retrying ...')
            continue

        # parse html
        html = etree.HTML(resp.content)

        # title
        try:
            title = html.find('.//title').text.split(' - ')[0].replace('/', '').strip()
            break
        except AttributeError:
            print('Retrying ...')
            continue

    if title is None:
        raise URLParseError

    image_urls = html.xpath('//img/@file')
    return title, image_urls
