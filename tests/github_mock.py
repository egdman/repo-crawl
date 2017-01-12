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

    CONTRIBUTORS_PTRN = re.compile(r'repos\/(.*)\/(.*)\/contributors\/?')

    def do_GET(self):
        
        result = re.search(self.CONTRIBUTORS_PTRN, self.path)

        if result:

            sleep(2. + 2.*random.random())

            user_name = result.group(1)
            repo_name = result.group(2)

            # Add response status code.
            self.send_response(requests.codes.ok)

            # Add response headers.
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('X-RateLimit-Remaining', 5000)
            self.send_header('Thread-Name', currentThread().getName())
            self.end_headers()

            # Add response content.
            response_content = json.dumps(self.fake_data(repo_name))

            self.wfile.write(response_content.encode('utf-8'))
            return     



    def fake_data(self, repo_name):
        contr_names = list(repo_name + "_contrib{}".format(cnum) for cnum in range(4))
        return list({
                'login': contr_name,
                'repos_url': 'https://api.github.com/users/{}/repos'.format(contr_name),
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