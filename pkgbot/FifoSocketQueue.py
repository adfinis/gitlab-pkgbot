#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
import signal
import socket
import time
import threading
import Queue
import functools


FIFO_SOCKET="/home/eni/run/aptly-fifo.sock"
FIFO_MAX_LEN=1024


class SocketFifoQueue(threading.Thread):
    """
    Implement a simple fifo socket queue
    """
    def __init__(self):
        threading.Thread.__init__(self)
        self.queue = Queue.Queue()
        self.request_exit = False
        self.jobcount = 0
        signal.signal(signal.SIGTERM, self.catch_exit_signal)


    def add(self, item):
        if item:
            print("new incoming item")
        self.queue.put(item)


    def exit(self):
        self.request_exit = True
        self.queue.put(False)
        print("EXIT requested")


    def catch_exit_signal(self, signum, frame):
        self.exit()
        self.add(False)


    def process_item(self, item):
        print("{0}: processing: {1}".format(self.jobcount, item))
        time.sleep(10)
        print("{0}: processing: {1} done".format(self.jobcount, item))
        self.jobcount+=1


    def run(self):
        while True:
            item = self.queue.get(block=True)
            if item:
                self.process_item(item)
            if self.request_exit:
                print("fifo-thread: exit")
                os.close(self.fifo)
                sys.exit(0)
                return


    def sock_loop(self):
        self.fifo = os.open(FIFO_SOCKET, os.O_NONBLOCK)
        try:
            while True and not self.request_exit:
                data = os.read(self.fifo, FIFO_MAX_LEN)
                if data:
                    d_clean = data.strip()
                    self.add(d_clean)
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.exit()
            self.add(False)



def main():

    try:
        os.mkfifo(FIFO_SOCKET)
    except OSError, e:
        print "Failed to create FIFO: %s" % e

    queue_thread = SocketFifoQueue()
    queue_thread.start()
    queue_thread.sock_loop()



if __name__ == '__main__':
    main()
