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
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_0) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/31.0.1650.57 Safari/537.36'
    )
}

BASE_URL = 'http://ck101.com/'

THREAD_CHUNK_SIZE = 3
IMAGE_CHUNK_SIZE = 3


class ThreadsFetcher(object):
    def __init__(self, client):
        self.client = client

    async def fetch(self, url):
        if 'thread' in url:
            return set([url])
        else:
            async with self.client.get(url, headers=REQUEST_HEADERS) as resp:
                assert resp.status == 200
                html = etree.HTML(await resp.read())
                return set(html.xpath('//a/@href'))


class ImagesFetcher(object):
    def __init__(self, client, threads_fetcher, base_folder):
        self.client = client
        self.threads_fetcher = threads_fetcher
        self.base_folder = base_folder

    async def fetch(self, url):
        threads_urls = await self.threads_fetcher.fetch(url)
        images = []
        for chunked_threads_urls in chunked(threads_urls, THREAD_CHUNK_SIZE):
            done, _ = await asyncio.wait([
                self.fetch_threads(threads_url)
                for threads_url in chunked_threads_urls
            ])
            images.extend(filter(None, [i.result() for i in done]))

        for title, thread_id, image_urls in images:
            # create target folder for saving images
            folder = os.path.join(self.base_folder,
                                  '%s - %s' % (thread_id, title))
            if not os.path.exists(folder):
                os.mkdir(folder)

            for chunked_image_urls in chunked(image_urls, IMAGE_CHUNK_SIZE):
                await asyncio.wait([
                    self.get_image(image_url, folder)
                    for image_url in chunked_image_urls
                ])

    async def get_image(self, image_url, folder):
        filename = image_url.rsplit('/', 1)[1]

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

    async def fetch_threads(self, url):
        url = BASE_URL + url if not url.startswith('http') else url
        m = re.match('thread-(\d+)-.*', url.rsplit('/', 1)[1])
        if not m:
            return

        print('\nVisit %s' % (url))

        thread_id = m.group(1)

        # parse title and images
        try:
            title, image_urls = await self.parse_url(url)
        except URLParseError:
            sys.exit('Oops, can not fetch the page')

        return title, thread_id, image_urls

    async def parse_url(self, thread_url):
        async with self.client.get(thread_url,
                                   headers=REQUEST_HEADERS) as resp:
            assert resp.status == 200
            html = etree.HTML(await resp.read())
            title = (html.find('.//title').text
                     .split(' - ')[0]
                     .replace('/', '')
                     .strip())

            image_urls = (url for url in html.xpath('//img/@file')
                          if url.startswith('http'))
            return title, image_urls


def iloveck101(url):
    """
    Determine the url is valid.
    And check if the url contains any thread link or it's a thread.
    """

    if 'ck101.com' not in url:
        sys.exit('This is not ck101 url')

    # create `iloveck101` folder in ~/Pictures
    base_folder = get_pic_base_folder()
    if not os.path.exists(base_folder):
        os.mkdir(base_folder)

    loop = asyncio.get_event_loop()
    client = aiohttp.ClientSession(loop=loop)

    threads_fetcher = ThreadsFetcher(client)
    images_fetcher = ImagesFetcher(client, threads_fetcher, base_folder)

    try:
        loop.run_until_complete(images_fetcher.fetch(url))
    except KeyboardInterrupt:
        print('I love ck101')

    client.close()


def main():
    try:
        url = sys.argv[1]
    except IndexError:
        sys.exit('Please provide URL from ck101')

    iloveck101(url)
