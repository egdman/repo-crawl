import re
import requests
import json
import asyncio
import aiohttp

from time import sleep

from nose.tools import assert_true, assert_in, nottest

from readem.async_req_aiohttp import start_urls, fetch

from github_mock import get_free_port, start_mock_server

class TestAPICalls(object):
    @classmethod
    def setup_class(cls):
        # start server
        cls.mock_server_port = get_free_port()
        start_mock_server(cls.mock_server_port)

        # replace real API address with localhost
        cls.test_urls = list(
            re.sub(
                'https://api.github.com',
                'http://localhost:{}'.format(cls.mock_server_port),
                url) 
            for url in start_urls)


        # do not replace (test real API)
        # cls.test_urls = start_urls

        # with open('testurls.log', 'w') as urlfile:
        #     for url in cls.test_urls:
        #         urlfile.write(url + '\n')
        

    @nottest
    async def test_fetch(self, url, session):
        data, limit = await fetch(url, session)
        assert_true(data)
        assert_in('login', data[0])
        assert_in('repos_url', data[0])

        with open('testresponses_async.json', 'w') as respfile:
            json.dump(data, respfile, indent=4)



    def test_get_contributors(self):
        test_url = self.test_urls[0]
        loop = asyncio.get_event_loop()

        with aiohttp.ClientSession(loop=loop) as session:
            loop.run_until_complete(self.test_fetch(test_url, session))