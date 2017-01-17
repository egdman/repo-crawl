import requests
import json
import asyncio
import aiohttp
import re
import os.path
import logging
import random
from functools import partial
from time import sleep, time


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



class CrawlError(Exception): pass


class BadServerResponse(CrawlError):
    def __init__(self, message, resp_headers, resp_body):
        self.message = message
        self.resp_headers = resp_headers
        self.resp_body = resp_body

    def report(self):
        report = self.message + '\n'
                
        for header in self.resp_headers:
            report += "{} : {}\n".format(header, self.resp_headers[header])

        report += "BEGIN_BODY\n"
        report += self.resp_body + '\n'
        report += "END_BODY\n"
        return report


class ParseError(CrawlError):
    def __init__(self, message):
        self.message = message

    def report(self):
        return self.message



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

    def __init__(self, start_urls, access_token=None, rate_of_requests = 1.):
        
        self.url_queue = asyncio.Queue()
        for url in start_urls: self.url_queue.put_nowait(url)

        self.access_token = access_token

        self.repo_contribs_ptrn = re.compile(r'\/+repos\/+(.*?)\/+(.*?)\/+contributors\/?')
        self.user_repos_ptrn = re.compile(r'\/+users\/+(.*?)\/+repos\/?')

        self.target_rate_of_req = rate_of_requests
        self.last_resp_time = time()



    async def fetch(self, url, session):

        if self.access_token is not None:
            url_with_token = url + "?access_token={}".format(self.access_token)
        else:
            url_with_token = url

        async with session.get(url_with_token) as resp:

            status_code = resp.status
            resp_body = await resp.text()

            resp_data = []

            # try to decode JSON response
            try:
                resp_data = json.loads(resp_body)
            except json.decoder.JSONDecodeError as ex:
                logging.info(
                    ParseError(
                        message="JSON could not decode the following text:\n{}".format(resp_body)
                    ).report()
                )
            
            if status_code != 200:
                logging.info(BadServerResponse(
                    message = "got status {} from {}".format(status_code, url),
                    resp_headers = resp.headers,
                    resp_body = resp_body).report())

                # if code is not 200, the decoded JSON will be wrong, so we ditch it
                resp_data = []

            # we need this header to know how many requests left
            # if it's not there, raise error
            if 'X-RateLimit-Remaining' not in resp.headers:

                raise BadServerResponse(
                    message = "x-ratelimit-remaining not in headers, url: {}".format(url),
                    resp_headers = resp.headers,
                    resp_body = resp_body)

            limit = resp.headers['X-RateLimit-Remaining']

            return resp_data, limit

            



    def schedule_request(self, url, session):
        contribs_match = re.search(self.repo_contribs_ptrn, url)
        repos_match = re.search(self.user_repos_ptrn, url)

        fut = asyncio.ensure_future(self.fetch(url, session))

        # add appropriate callback

        if contribs_match:
            cback = partial(self.handle_response, handler=self.process_repo_contribs)
        elif repos_match:
            cback = partial(self.handle_response, handler=self.process_user_repos)

        fut.add_done_callback(cback)




    async def run(self, loop):

        async with aiohttp.ClientSession(loop=loop) as session:
            while True:

                await asyncio.sleep(1. / self.target_rate_of_req)
                url = await self.url_queue.get()
                self.schedule_request(url, session)



    def handle_response(self, future, handler):
        time_since_last = time() - self.last_resp_time
        self.last_resp_time = time()
        print("dT = " + str(time_since_last))
        try:
            handler(future)
        except KeyError as exc:
            logging.info("Got error when parsing response: key {} not found.".format(exc))



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





def except_handler(loop, context, logger):
    ex = context['exception']
    if isinstance(ex, CrawlError):
        logger.info(ex.report())
    else:
        raise ex




def main():
    # Setup fake server on localhost
    start_urls = setup_mock()


    logging.basicConfig(
        filename = 'readem_crawler.log',
        level = logging.INFO,
        format='%(levelname)s:%(message)s')

    logger = logging.getLogger(__name__)


    loop = asyncio.get_event_loop()
    loop.set_exception_handler(partial(except_handler, logger=logger))

    crawler = GithubCrawler(start_urls, access_token=access_token)
    loop.run_until_complete(crawler.run(loop))


if __name__ == '__main__':
    main()