#!/usr/bin/env python

import argparse
import logging.handlers
import sys

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except:
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
try:
    import SocketServer
except:
    import socketserver as SocketServer
import os
import pandas as pd
from urllib.parse import urlparse, parse_qs


# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
    def __init__(self, logger, level):
        """Needs a logger and a logger level."""

        self.logger = logger
        self.level = level

    def write(self, message):
        # Only log if there is a message (not just a new line)
        if message.rstrip() != "":
            self.logger.log(self.level, message.rstrip())

    def flush(self):
        pass


def load_db(db_file):
    if not os.path.isfile(db_file):
        with open(db_file, 'w') as f:
            f.write(',title,author\n')

    df = pd.read_csv(db_file, header=0, names=['title', 'author'])

    return df


def already_exists_book(title, df):
    print("New title: %s \nList of titles: %s" % (title, df.title))
    # checks in lowercase
    return title.lower() in [t.lower() for t in df.title.values]


class S(BaseHTTPRequestHandler):
    data_file = './data.csv'

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        content = parse_qs(urlparse(self.path).query)
        df = load_db(self.data_file)
        print("Content: %s" % content)
        if 'title' in content.keys():
            title = content['title'][0].lower()
            author = content['author'][0].lower()

            if already_exists_book(title, df):
                print("Book already present")
                self.wfile.write(b'Book already present.')
            else:
                df = df.append({'title': title, 'author': author},
                               ignore_index=True).sort_values('title')
                print("DF: %s" % df)
                df.to_csv(self.data_file)
                print("Book %s - %s added to the library." % (title, author))
                self.wfile.write("Book '{} - {}' added to the library.".format(title, author).encode())

        else:
            print("No title found, returning list of books.")
            self.wfile.write(
                '<html><body><h1>Finished Books {}</h1>'.format(df.shape[0]).encode())
            for _, row in df.iterrows():
                self.wfile.write(
                    '<p>{}, {}</p>'.format(row.title.title(), row.author.title()).encode())
            self.wfile.write('</body></html>'.encode())

    def do_HEAD(self):
        print("Ignoring HEAD request")

    def do_POST(self):
        print("Ignoring POST request")


def run(port, server_class=HTTPServer, handler_class=S):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print('Starting httpd...')
    try:
        # Listen for requests indefinitely
        httpd.serve_forever()
    except KeyboardInterrupt:
        # A request to terminate has been received, stop the server
        print("\nShutting down...")
        httpd.socket.close()

LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"

# Define and parse command line arguments
parser = argparse.ArgumentParser(
    description="My simple AWS book python service")
parser.add_argument("-l", "--log", help="File to write log to",
                    default="./aws-books.log")
parser.add_argument("-p", "--port",
                    help="Port where the webhooks will be listening",
                    default=83)

# If the log file is specified on the command line then override the default
args = parser.parse_args()
LOG_FILENAME = args.log
PORT = int(args.port)

# Configure logging to log to a file, making a new file at midnight and keeping the last 3 day's data
# Give the logger a unique name (good practice)
logger = logging.getLogger(__name__)
# Set the log level to LOG_LEVEL
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME,
                                                    when="midnight",
                                                    backupCount=3)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)

# Replace stdout with logging to file at INFO level
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)

run(port=PORT)
