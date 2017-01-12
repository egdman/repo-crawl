import re
import requests
import json

from time import sleep

from nose.tools import assert_true

from thief.async_req_aiohttp import start_urls

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


        # # do not replace (test real API)
        # cls.test_urls = start_urls

        with open('testurls.log', 'w') as urlfile:
            for url in cls.test_urls:
                urlfile.write(url + '\n')
        



    def test_get_contributors(self):
        test_urls = list(url + '/contributors' for url in self.test_urls)

        with open('testresponses.json', 'w') as respfile:
            for url in test_urls:
                
                resp = requests.get(url)
                assert_true(resp)

                resp_data = json.loads(resp.text)
                
                json.dump(resp_data, respfile, indent=4)

                