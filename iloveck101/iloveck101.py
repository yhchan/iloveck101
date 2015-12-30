import os
import sys
import re

import gevent
from gevent import monkey

monkey.patch_all()

import requests
from lxml import etree
from more_itertools import chunked

from .utils import get_image_info, get_pic_base_folder
from .exceptions import URLParseError

REQUEST_HEADERS = {
    'User-agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_0) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/31.0.1650.57 Safari/537.36'
    )
}

BASE_URL = 'http://ck101.com/'
CHUNK_SIZE = 3


def iloveck101(url):
    """
    Determine the url is valid.
    And check if the url contains any thread link or it's a thread.
    """

    if 'ck101.com' not in url:
        sys.exit('This is not ck101 url')

    try:
        threads = [url] if 'thread' in url else retrieve_thread_list(url)
        for thread in filter(None, threads):
            retrieve_thread(thread)
    except KeyboardInterrupt:
        print('I love ck101')


def retrieve_thread_list(url):
    """ The url may contains many thread links. We parse them out. """
    resp = requests.get(url, headers=REQUEST_HEADERS)
    html = etree.HTML(resp.content)
    yield from html.xpath('//a/@href')


def parse_url(url):
    """ parse image_url from given url """
    title = None
    for attemp in range(3):
        try:
            resp = requests.get(url, headers=REQUEST_HEADERS)
            resp.raise_for_status()

            html = etree.HTML(resp.content)
            title = (html.find('.//title').text
                     .split(' - ')[0]
                     .replace('/', '')
                     .strip())
            break
        except (AttributeError, requests.exceptions.HTTPError):
            print('Retrying ...')
            continue
    else:
        raise URLParseError

    image_urls = html.xpath('//img/@file')
    return title, image_urls


def retrieve_thread(url):
    """
    download images from given ck101 URL
    """

    # check if the url has http prefix
    url = BASE_URL + url if not url.startswith('http') else url

    # find thread id
    m = re.match('thread-(\d+)-.*', url.rsplit('/', 1)[1])
    if not m:
        return

    print('\nVisit %s' % (url))

    thread_id = m.group(1)

    # create `iloveck101` folder in ~/Pictures
    base_folder = get_pic_base_folder()
    if not os.path.exists(base_folder):
        os.mkdir(base_folder)

    # parse title and images
    try:
        title, image_urls = parse_url(url)
    except URLParseError:
        sys.exit('Oops, can not fetch the page')

    # create target folder for saving images
    folder = os.path.join(base_folder, "%s - %s" % (thread_id, title))
    if not os.path.exists(folder):
        os.mkdir(folder)

    def process_image_worker(image_url):
        filename = image_url.rsplit('/', 1)[1]

        # ignore useless image
        if not image_url.startswith('http'):
            return

        # fetch image
        print('Fetching %s ...' % image_url)
        resp = requests.get(image_url, headers=REQUEST_HEADERS)

        # ignore small images
        content_type, width, height = get_image_info(resp.content)
        if width < 400 or height < 400:
            print("image is too small")
            return

        # save image
        with open(os.path.join(folder, filename), 'wb+') as f:
            f.write(resp.content)

    for chunked_image_urls in chunked(image_urls, CHUNK_SIZE):
        jobs = [gevent.spawn(process_image_worker, image_url)
                for image_url in chunked_image_urls]
        gevent.joinall(jobs)


def main():
    try:
        url = sys.argv[1]
    except IndexError:
        sys.exit('Please provide URL from ck101')

    iloveck101(url)
