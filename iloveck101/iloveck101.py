import aiohttp
import asyncio
import os
import sys
import re

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

THREAD_CHUNK_SIZE = 3
IMAGE_CHUNK_SIZE = 3


class ck101Fetcher(object):
    def __init__(self, client):
        self.client = client

    async def retrieve_thread_list(self, url):
        """ The url may contains many thread links. We parse them out. """
        async with self.client.get(url, headers=REQUEST_HEADERS) as resp:
            assert resp.status == 200
            html = etree.HTML(await resp.read())
            return set([url for url in html.xpath('//a/@href')])

    async def parse_url(self, url):
        """ parse image_url from given url """
        for attemp in range(3):
            try:
                async with self.client.get(url,
                                           headers=REQUEST_HEADERS) as resp:
                    assert resp.status == 200
                    html = etree.HTML(await resp.read())
                    title = (html.find('.//title').text
                             .split(' - ')[0]
                             .replace('/', '')
                             .strip())
                    break
            except (AttributeError, AssertionError):
                print('Retrying ...')
                continue
        else:
            raise URLParseError

        image_urls = html.xpath('//img/@file')
        return title, image_urls

    async def get_image(self, image_url, folder):
        filename = image_url.rsplit('/', 1)[1]

        # ignore useless image
        if not image_url.startswith('http'):
            return

        # fetch image
        print('Fetching %s ...' % image_url)
        async with self.client.get(image_url,
                                   headers=REQUEST_HEADERS) as resp:
            assert resp.status == 200
            content = await resp.read()
            # ignore small images
            content_type, width, height = get_image_info(content)
            if width < 400 or height < 400:
                print("image is too small")
                return

            # save image
            with open(os.path.join(folder, filename), 'wb+') as f:
                f.write(content)


def iloveck101(url):
    """
    Determine the url is valid.
    And check if the url contains any thread link or it's a thread.
    """

    if 'ck101.com' not in url:
        sys.exit('This is not ck101 url')

    loop = asyncio.get_event_loop()
    client = aiohttp.ClientSession(loop=loop)

    fetcher = ck101Fetcher(client)

    async def retrieve_threads(url):
        threads = ([url] if 'thread' in url
                   else await fetcher.retrieve_thread_list(url))

        for chunked_threads in chunked(threads, THREAD_CHUNK_SIZE):
            await asyncio.wait([
                retrieve_thread(fetcher, thread)
                for thread in chunked_threads
            ])

    try:
        loop.run_until_complete(retrieve_threads(url))
    except KeyboardInterrupt:
        print('I love ck101')

    client.close()


async def retrieve_thread(fetcher, url):
    """ download images from given ck101 URL """

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
        title, image_urls = await fetcher.parse_url(url)
    except URLParseError:
        sys.exit('Oops, can not fetch the page')

    # create target folder for saving images
    folder = os.path.join(base_folder, "%s - %s" % (thread_id, title))
    if not os.path.exists(folder):
        os.mkdir(folder)

    for chunked_image_urls in chunked(image_urls, IMAGE_CHUNK_SIZE):
        await asyncio.wait([
            fetcher.get_image(image_url, folder)
            for image_url in chunked_image_urls
        ])


def main():
    try:
        url = sys.argv[1]
    except IndexError:
        sys.exit('Please provide URL from ck101')

    iloveck101(url)
