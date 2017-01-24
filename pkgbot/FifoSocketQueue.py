#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
import time
import Queue
import signal
import socket
import logging
import argparse
import threading
import functools
import subprocess

from pprint import pprint

FIFO_SOCKET="/home/eni/run/aptly-fifo.sock"
UF_JOB_FILE="/home/eni/adsy/gitlab-pkgbot/pkgbot/job-save"
FIFO_MAX_LEN=2048


# init logging
def get_logger( prefix="fifo-socket-queue", project=False ):
    loggername = prefix
    if project:
        loggername = "{0} - {1}".format(prefix, project)
    logger = logging.getLogger(loggername)
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setFormatter(log_formatter)
    logger.setLevel(10)
    logger.addHandler(ch)
    return logger

logger = get_logger()



class SocketFifoQueue(threading.Thread):
    """
    Implement a simple fifo socket queue
    """
    def __init__(self, fifo, save_file=False):
        threading.Thread.__init__(self)
        self.fifo = fifo
        self.queue = Queue.Queue()
        self.request_exit = False
        signal.signal(signal.SIGTERM, self.catch_exit_signal)
        if save_file:
            self.save_file = save_file
            if os.access(self.save_file, os.W_OK):
                self.load_jobs()


    def add(self, item):
        """
        Add an item to the queue
        """
        if item:
            logger.debug("New incoming item")
        self.queue.put(item)


    def exit(self):
        """
        Request an exit
        """
        self.request_exit = True
        self.queue.put(False)
        logger.debug("exit requested")


    def save_jobs(self):
        """
        If an exit is requested and there are still jobs in the queue,
        save them to a file
        """
        if not self.save_file:
            return
        if not os.access(self.save_file, os.W_OK):
            return
        size = self.queue.qsize()
        unfinished = []
        while True:
            try:
                item = self.queue.get_nowait()
                if item:
                    unfinished.append(item)
            except Queue.Empty:
              break
        if len(unfinished)<1:
            return
        logger.info("{0} unfinished jobs in queue, saving to disk".format(
            len(unfinished)
        ))
        with open (self.save_file, 'w') as savefile:
            savefile.write("\n".join(unfinished))


    def load_jobs(self):
        """
        Load Jobs from disk to queue
        """
        if not self.save_file:
            return
        with open (self.save_file) as savefile:
            jobs = savefile.readlines()
            if len(jobs)<1:
                return
            logger.info("{0} unfinished jobs found on disk, loading".format(len(jobs)))
            for job in jobs:
                self.queue.put(job.strip())
            # empty file
            open(self.save_file, 'w').close()


    def catch_exit_signal(self, signum, frame):
        """
        Gets called when SIGTERM is recived
        """
        self.exit()


    def process_item(self, item):
        """
        Process an item from queue
        """
        arr = item.split(" ")
        logger.info("processing: '{0}'".format(item))
        try:
            subprocess.check_call( arr, stderr=subprocess.STDOUT )
        except (OSError, subprocess.CalledProcessError) as e:
            logger.warn(e)
        logger.info("done processing: '{0}'".format(item))


    def run(self):
        """
        Main loop for queue processing
        """
        # run forever
        while True:
            item = self.queue.get(block=True)
            if item:
                self.process_item(item)
            # exit requested, finish current job and close
            if self.request_exit:
                logger.debug("processing exit")
                os.close(self.fifo)
                self.save_jobs()
                sys.exit(0)
                return


    def start_sock(self):
        """
        Main loop for socket reading
        """
        try:
            while True and not self.request_exit:
                data = os.read(self.fifo, FIFO_MAX_LEN)
                if data:
                    d_clean = data.strip()
                    d_cmds  = data.strip().split("\n")
                    for cmd in d_cmds:
                        self.add(cmd)
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.exit()



def main():

    parser = argparse.ArgumentParser(
                description="FIFO socket queue"
             )
    parser.add_argument(
                "--socket",
                default=FIFO_SOCKET,
                help="Socket file"
             )
    parser.add_argument(
                "--save-file",
                default=UF_JOB_FILE,
                help="File to save unfinished jobs",
             )
    args = parser.parse_args()


    try:
        os.mkfifo(args.socket)
    except OSError, e:
        logger.warn("Failed to create FIFO: {0}".format(e))

    fifo = os.open(args.socket, os.O_NONBLOCK)
    queue_thread = SocketFifoQueue(fifo, args.save_file)
    queue_thread.start()
    queue_thread.start_sock()



if __name__ == '__main__':
    main()
