import requests
import json
import asyncio
import aiohttp
import re
import os.path
import logging
import random
from functools import partial
from time import sleep


from tests.github_mock import get_free_port, start_mock_server

access_token_path = os.path.join(os.path.dirname(__file__), 'access_token.SECRET')

if os.path.isfile(access_token_path):
    access_token = open(access_token_path, 'r').read()
else:
    access_token = None


start_url = 'https://api.github.com/repos/git/git/contributors'

start_urls = [
    'https://api.github.com/repos/git/git',
    'https://api.github.com/repos/atom/atom',
    'https://api.github.com/repos/meteor/meteor',
    'https://api.github.com/repos/django/django',
    'https://api.github.com/repos/apple/swift',
    'https://api.github.com/repos/d3/d3',
    'https://api.github.com/repos/matplotlib/matplotlib',
    'https://api.github.com/repos/cms-sw/cmssw'
]

start_urls = list(url + '/contributors' for url in start_urls)





def setup_mock():
    # get port
    mock_server_port = get_free_port()

    # start server
    start_mock_server(mock_server_port)

    # replace API address with localhost
    test_urls = list(
        re.sub(
            'https://api.github.com',
            'http://localhost:{}'.format(mock_server_port),
            url) 
        for url in start_urls)

    return test_urls



async def print_stuff():
    tick = True
    while True:
        await asyncio.sleep(.5)
        print('////') if tick else print('\\\\\\\\')
        tick = not tick



class GithubCrawler(object):

    def __init__(self, start_urls, access_token=None):

        self.logger = logging.getLogger(__name__)
        
        self.url_queue = asyncio.Queue()
        for url in start_urls: self.url_queue.put_nowait(url)

        self.access_token = access_token

        self.repo_contribs_ptrn = re.compile(r'\/repos\/(.*)\/(.*)\/contributors\/?')
        self.user_repos_ptrn = re.compile(r'\/users\/(.*)\/repos\/?')

        self.rate_of_req = 0.
        self.target_rate = 1.  # do this many requests per second



    async def fetch(self, url, session):

        if self.access_token is not None:
            url_with_token = url + "?access_token={}".format(self.access_token)
        else:
            url_with_token = url

        async with session.get(url_with_token) as resp:

            status_code = resp.status
            resp_string = await resp.text()

            try:
                resp_data = json.loads(resp_string)
            except json.decoder.JSONDecodeError as ex:
                self.logger.info("JSON could not decode the following text:\n{}".format(resp_string))
                resp_data = []


            if status_code != 200:
                report = "got status {} from {}\n".format(status_code, url)
                
                for header in resp.headers:
                    report += "{} : {}\n".format(header, resp.headers[header])

                report += "BEGIN_BODY\n"
                report += resp_string + '\n'
                report += "END_BODY\n"

                self.logger.info(report)
                return resp_data, 0


            if 'X-RateLimit-Remaining' not in resp.headers:
                self.logger.info("x-ratelimit-remaining not in headers, url: {}".format(url))
                return resp_data, 0

            limit = resp.headers['X-RateLimit-Remaining']

            # print("got status {} from {}".format(status_code, url))

            return resp_data, limit



    def schedule_request(self, url, session):
        contribs_match = re.search(self.repo_contribs_ptrn, url)
        repos_match = re.search(self.user_repos_ptrn, url)

        fut = asyncio.ensure_future(self.fetch(url, session))

        # add appropriate callback
        if contribs_match:
            fut.add_done_callback(self.process_repo_contribs)
        elif repos_match:
            fut.add_done_callback(self.process_user_repos)




    async def run(self, loop):

        async with aiohttp.ClientSession(loop=loop) as session:
            while True:

                url = await self.url_queue.get()
                self.schedule_request(url, session)

                # TODO add some code to handle throttling



    def process_repo_contribs(self, future):
        json_data, limit = future.result() 
        contrib_repos_urls = list(json_obj['repos_url'] for json_obj in json_data)
        contrib_logins = list(json_obj['login'] for json_obj in json_data)
        print("{} contributors".format(len(json_data)))
        print("limit: {}".format(limit))
        print("::::::::::::::::::::::::::::::::::::::::")
        for url in contrib_repos_urls: self.url_queue.put_nowait(url)


    def process_user_repos(self, future):
        json_data, limit = future.result() 
        repo_contribs_urls = list(json_obj['contributors_url'] for json_obj in json_data)
        repo_urls = list(json_obj['url'] for json_obj in json_data)

        print("{} repos".format(len(json_data)))
        print("limit: {}".format(limit))
        print("++++++++++++++++++++++++++++++++++++++++")
        for url in repo_contribs_urls: self.url_queue.put_nowait(url)


def main():

    logging.basicConfig(
        filename = 'readem_crawler.log',
        level = logging.INFO,
        format='%(levelname)s:%(message)s')

    # Setup fake server on localhost
    start_urls = setup_mock()

    loop = asyncio.get_event_loop()
    # loop.run_until_complete(run(loop, start_urls))

    crawler = GithubCrawler(start_urls, access_token=access_token)
    loop.run_until_complete(crawler.run(loop))


if __name__ == '__main__':
    main()