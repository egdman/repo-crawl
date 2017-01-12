import requests
import json
import asyncio
import aiohttp
import re
import os.path
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



async def fetch(url, session):
    
    if access_token is not None:
        url_with_token = url + "?access_token={}".format(access_token)
    else:
        url_with_token = url

    async with session.get(url_with_token) as resp:

        status_code = resp.status
        limit = resp.headers['X-RateLimit-Remaining']
        resp_data = json.loads(await resp.text())

        print("got status {} from {}".format(status_code, url))
        
    # with open('res.json', 'w') as resfile:
        # json.dump(resp_data, resfile, indent=4)

        # print("{} contributors".format(len(resp_data)))
        # print("requests remaining : {}".format(limit))
        # print('thread : {}'.format(resp.headers['Thread-Name']))
        return resp_data, limit






async def run(loop, urls):
    async with aiohttp.ClientSession(loop=loop) as session:
        # for url in urls: await fetch(url, session)

        tasks = list(asyncio.ensure_future(fetch(url, session)) for url in urls)
        # for task in tasks: task.add_done_callback()
        retv = await asyncio.wait(tasks)

        results = list(fin_task.result() for fin_task in retv[0])
        for (data, limit) in results:
            print("{} contributors".format(len(data)))
            print("requests remaining : {}".format(limit))




def main():
    # Setup fake server on localhost
    # start_urls = setup_mock()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(loop, start_urls))


if __name__ == '__main__':
    main()



# print(asyncio.get_event_loop_policy())


# def get_repos(init_repo_url, max_num_repos):
#   explored_repos = set()
#   new_repos = deque([init_repo_url])

#   explored_users = set()

#   while len(explored_repos) < max_num_repos:
#       if len(new_repos) == 0:
#           print("FINISHED EARLY")
#           break

#       repo_url = new_repos.popleft()
#       explored_repos.append(repo_url)

#       print(" explored repos: {}".format(len(explored_repos)))
#       print("total number of repos: {}".format(len(new_repos) + len(explored_repos)))




