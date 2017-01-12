import requests
import json
import asyncio
from functools import partial


access_token = "b3135d33c740a7f23684cc009658301887eafc30"

start_url = 'https://api.github.com/repos/git/git/contributors'


# this is a callback
def process_response(fut, url):
	resp = fut.result()

	limit = resp.headers['X-RateLimit-Remaining']
	enc_name = resp.encoding
	resp_data = json.loads(resp.text)


	print("got status {} from {}".format(resp.status_code, url))
	print("X-RateLimit-Remaining = {}".format(limit))


	with open('res.json', 'w') as resfile:
		json.dump(resp_data, resfile, indent=4)



async def print_stuff():
	tick = True
	while True:
		await asyncio.sleep(.5)
		print('( ') if tick else print(' )')
		tick = not tick



async def send_request(url):
	url_with_token = url + "?access_token={}".format(access_token)
	loop = asyncio.get_event_loop()
	fut = loop.run_in_executor(None, requests.get, url_with_token)
	fut.add_done_callback(
		partial(process_response, url=url))

	print("request sent...")
	print(fut.__class__)
	await fut

	


def main():
	loop = asyncio.get_event_loop()
	loop.run_until_complete(
		asyncio.gather(
			send_request(start_url),
			print_stuff()
		)
	)



if __name__ == '__main__':
	main()



# print(asyncio.get_event_loop_policy())


# def get_repos(init_repo_url, max_num_repos):
# 	explored_repos = set()
# 	new_repos = deque([init_repo_url])

# 	explored_users = set()

# 	while len(explored_repos) < max_num_repos:
# 		if len(new_repos) == 0:
# 			print("FINISHED EARLY")
# 			break

# 		repo_url = new_repos.popleft()
# 		explored_repos.append(repo_url)

# 		print(" explored repos: {}".format(len(explored_repos)))
# 		print("total number of repos: {}".format(len(new_repos) + len(explored_repos)))




