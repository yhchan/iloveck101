# coding: utf-8

import os
import unittest
import requests

from iloveck101.utils import parse_url, get_image_info
from iloveck101.iloveck101 import iloveck101, main
from iloveck101.exceptions import URLParseError
from httmock import urlmatch, HTTMock, all_requests


TEST_DIR = os.path.abspath(os.path.join(__file__, '..'))


@urlmatch(netloc=r'(.*\.)?imgs\.cc$')
def image_mock(url, request):
    image = os.path.join('fixtures', 'jYY7oMF.jpg')
    with open(os.path.join(TEST_DIR, image), 'rb') as f:
        content = f.read()

    response = requests.Response()
    response._content = content
    return response


@urlmatch(netloc=r'(.*\.)?ck101\.com$')
def thread_mock(url, request):
    html = os.path.join('fixtures', '2818521.html')
    with open(os.path.join(TEST_DIR, html)) as f:
        content = f.read()

    return content


@all_requests
def list_mock(url, request):
    html = os.path.join('fixtures', 'beauty.html')
    with open(os.path.join(TEST_DIR, html)) as f:
        content = f.read()

    return content

@all_requests
def error_mock(url, request):
    return {'status_code': 400, 'content': 'Hi'}



class CK101Test(unittest.TestCase):
    def setUp(self):
        self.thread_url = 'http://ck101.com/thread-2818521-1-1.html'
        self.list_url = 'http://ck101.com/beauty/'

    def test_thread(self):

        with HTTMock(thread_mock, image_mock):
            iloveck101(self.thread_url)


    def test_list(self):
        with HTTMock(list_mock, image_mock):
            iloveck101(self.list_url)

        with HTTMock(error_mock):
            iloveck101(self.list_url)

    def test_not_ck101(self):
        with self.assertRaises(SystemExit) as cm:
            iloveck101('http://google.com/')

        self.assertEqual(cm.exception.code, 'This is not ck101 url')

    def test_retry(self):
        with HTTMock(error_mock):
            with self.assertRaises(SystemExit) as cm:
                iloveck101(self.thread_url)

        self.assertEqual(cm.exception.code, 'Oops, can not fetch the page')

    def test_main(self):
        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 'This is not ck101 url')


class UtilsTest(unittest.TestCase):
    def setUp(self):
        self.url = 'http://ck101.com/thread-2818521-1-1.html'


    def test_parse_url(self):
        with HTTMock(thread_mock):
            title, image_urls = parse_url(self.url)

        self.assertEqual(title, u'蔡依林+心凌的綜合體？！19歲「無名時代的正妹」陳敬宣現在正翻了......')
        self.assertEqual(len(image_urls), 39)

    def test_parse_url_error(self):
        with HTTMock(error_mock):
            with self.assertRaises(URLParseError):
                title, image_urls = parse_url(self.url)

    def test_get_image_info(self):
        jpg = os.path.join('fixtures', 'jYY7oMF.jpg')

        with open(os.path.join(TEST_DIR, jpg), 'rb') as f:
            content_type, width, height = get_image_info(f.read())

        self.assertEqual(content_type, 'JPEG')
        self.assertEqual(width, 612)
        self.assertEqual(height, 612)


        png = os.path.join('fixtures', 'firefox.png')

        with open(os.path.join(TEST_DIR, png), 'rb') as f:
            content_type, width, height = get_image_info(f.read())

        self.assertEqual(content_type, 'PNG')
        self.assertEqual(width, 256)
        self.assertEqual(height, 256)


        gif = os.path.join('fixtures', 'firefox.gif')

        with open(os.path.join(TEST_DIR, gif), 'rb') as f:
            content_type, width, height = get_image_info(f.read())

        self.assertEqual(content_type, 'GIF')
        self.assertEqual(width, 256)
        self.assertEqual(height, 256)


if __name__ == '__main__':
    unittest.main()
