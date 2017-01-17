from http.server import BaseHTTPRequestHandler, HTTPServer
import re
import requests
import json
import socket
import random

from time import sleep
from threading import Thread, currentThread
from socketserver import ThreadingMixIn



class MockServerRequestHandler(BaseHTTPRequestHandler):

    REPO_CONTRIBS_PTRN = re.compile(r'\/+repos\/+(.*?)\/+(.*?)\/+contributors\/?')
    USER_REPOS_PTRN = re.compile(r'\/+users\/+(.*?)\/+repos\/?')

    def do_GET(self):
        
        contribs_match = re.search(self.REPO_CONTRIBS_PTRN, self.path)
        repos_match = re.search(self.USER_REPOS_PTRN, self.path)

        sleep(2. + .5*random.random())

        if contribs_match:

            user_name = contribs_match.group(1)
            repo_name = contribs_match.group(2)

            # Add response status code.
            self.send_response(requests.codes.ok)

            # Add response headers.
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('X-RateLimit-Remaining', 5000)
            self.end_headers()

            # Add response content.
            response_content = json.dumps(self.fake_contribs(repo_name))

            self.wfile.write(response_content.encode('utf-8'))
            return

        elif repos_match:

            user_name = repos_match.group(1)

            self.send_response(requests.codes.ok)

            # Add response headers
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('X-RateLimit-Remaining', 5000)
            self.end_headers()

            response_content = json.dumps(self.fake_repos(user_name))
            self.wfile.write(response_content.encode('utf-8'))
            return

        else:
            self.send_response(404)

            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('X-RateLimit-Remaining', 5000)
            self.end_headers()

            self.wfile.write(''.encode('utf-8'))
            return



    def fake_repos(self, user_name):
        (host, port) = self.server.server_address
        domain = 'http://{}:{}'.format(host, port)

        repo_names = list(user_name + "_repo{}".format(rnum) for rnum in range(2))

        data = []
        for repo_name in repo_names:

            full_name = '{}/{}'.format(user_name, repo_name)
            full_url = '{}/repos/{}'.format(domain, full_name)
            data.append({
                'name': repo_name,
                'full_name': full_name,
                'url': full_url,
                'contributors_url': '{}/contributors'.format(full_url),
            })

        return data
        


    def fake_contribs(self, repo_name):
        (host, port) = self.server.server_address
        domain = 'http://{}:{}'.format(host, port)
        contr_names = list(repo_name + "_contrib{}".format(cnum) for cnum in range(2))
        return list({
                'login': contr_name,
                'repos_url': '{}/users/{}/repos'.format(domain, contr_name),
            } for contr_name in contr_names)




class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def get_free_port():
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    address, port = s.getsockname()
    s.close()
    return port


def start_mock_server(port):
    mock_server = ThreadedHTTPServer(('localhost', port), MockServerRequestHandler)
    mock_server_thread = Thread(target=mock_server.serve_forever)
    mock_server_thread.setDaemon(True)
    mock_server_thread.start()