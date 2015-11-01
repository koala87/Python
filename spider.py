#!/usr/bin/env python
#coding: utf-8

"""
@Function: Multiple threads download lrc from Baidu
@Author: Yingqi Jin
@Date: Nov. 1st, 2015
@Description:
    Download lrc from Baidu, eg, url='www.baidu.com/s?wd="北京欢迎你"'

    Three queues -- SONG_QUEUE, HTML_QUEUE and LRC_QUEUE
    Queue is suitable for producer/consumer model and thread safe
    SONG_QUEUE stores songs to download
    ThreadFillSong to fill SONG_QUEUE
    ThreadDownload to download page and fill HTML_QUEUE
    ThreadDatamine to parse page and fill LRC_QUEUE
    ThreadWriteLrc to insert LRC_QUEUE into database 
    ThreadMonitor to display info
"""


import sys
import pdb
import urllib
import urllib2
from Queue import Queue
from time import time, sleep
from bs4 import BeautifulSoup
from threading import Thread, Lock 
from optparse import OptionParser

# set at the options parsing 
SONG_LIST_FILE = ''
LRC_FILE = '' 
DOWNLOAD_THREAD_NUM = 0
DATAMINE_THREAD_NUM = 0
DEBUG = False 
VERBOSE = False 


# Do NOT change below items unless you know clearly what are you doing
START = time()
SONG_QUEUE = Queue()
HTML_QUEUE = Queue()
LRC_QUEUE = Queue()
PRINT_LOCK = Lock()

#!!! Not Thread Safe
SONG_NUM = 0 # total num in song queue
LRC_NUM = 0 # successful lrc num 
LRC_NUM_TOTAL = 0 # total num in lrc queue 


def eprint(str, errCode=1):
    """error print"""
    print str
    sys.exit(errCode)

def vprint(str):
    """verbose print"""
    if VERBOSE:
        PRINT_LOCK.acquire()
        print '[%-4d s]\t%s' % (time() - START, str)    
        PRINT_LOCK.release()

def dprint(str):
    "debug print"
    if DEBUG:
        PRINT_LOCK.acquire()
        print '[%-4d s]\t%s' % (time() - START, str)    
        PRINT_LOCK.release()



class ThreadFillSong(Thread):
    """fill song queue"""
    def __init__(self):
        Thread.__init__(self)
        self.th_name = self.getName()
        vprint('fork %s to fill song queue ...' % self.th_name)

    def run(self):
        """fill song queue"""
        try:
            with open(SONG_LIST_FILE) as fin:
                while True:
                    line = fin.readline()
                    if len(line) == 0:
                        break
                    line = line.strip()
                    SONG_QUEUE.put(line)
                    dprint('%-15s%-30s%s' % (self.th_name, '[fill song done]', line) )
                    #!!! use mutex when there are more threads
                    global SONG_NUM
                    SONG_NUM += 1
        except IOError:
            eprint('read %s failed!' % SONG_LIST_FILE)


class ThreadDownload(Thread):
    """open url and fill html page into queue"""
    def __init__(self):
        Thread.__init__(self)
        self.th_name = self.getName()
        vprint('fork %s to download page ...' % self.th_name)

    def get_html(self, song_name):
        question_word = song_name + ' 歌词'
        question_word = question_word.decode('utf-8').encode('gbk')
        url = "http://www.baidu.com/s?wd=" + urllib.quote(question_word)
        htmlpage = urllib2.urlopen(url).read()
        return htmlpage

    def run(self):
        while True:
            # get the first element and remove it from queue
            # thread blocks when queue is empty
            song = SONG_QUEUE.get(block=True)
            html = self.get_html(song)
            HTML_QUEUE.put( (song, html) )
            dprint('%-15s%-30s%s' % (self.th_name, '[download page done]', song) ) 
            

class ThreadDatamine(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.th_name = self.getName()
        vprint('fork %s to datamine lrc ...' % self.th_name)

    def __parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        block = soup.find_all('div', attrs={'class':'c-gap-top-small op-lrc-text-c'})
        lrc = ''
        if len(block) > 0:
            lrc = block[0].prettify().encode('utf-8')
        lines = lrc.split('<br/>')
        lines = [i.strip() for i in lines if len(i) > 0 and i.find('div') == -1]
        lrc = '\n'.join(lines) 
        return lrc

    def run(self):
        """parse html and find label <div class="c-gap-top-small op-lrc-text-c">...</div>
           return empty string if lrc is not found"""
        while True:
            song, html = HTML_QUEUE.get()
            lrc = self.__parse(html)
            LRC_QUEUE.put( (song, lrc) )
            dprint('%-15s%-30s%s' % (self.th_name, '[parse lrc done]', song) ) 


class ThreadWriteLrc(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.th_name = self.getName()
        vprint('fork %s to write lrc ...' % self.th_name)

    def run(self):
        """write lrc into db"""
        #!!! use mutex when there are more threads
        sep = '--------------------------------------------------\n'
        global LRC_NUM_TOTAL, LRC_NUM
        with open(LRC_FILE, 'w') as fout:
            while True:
                song, lrc = LRC_QUEUE.get()
                if lrc:
                    fout.write(sep + lrc + '\n\n')
                    dprint('%-15s%-30s%s' % (self.th_name, '[write lrc done]', song) ) 
                    LRC_NUM += 1
                LRC_NUM_TOTAL += 1


def display():
    vprint('song queue size:%-10d html queue size:%-10d lrc queue size:%-10d song num:%-10d total lrc num:%-10d lrc num:%d'
        % (SONG_QUEUE.qsize(), HTML_QUEUE.qsize(), LRC_QUEUE.qsize() , SONG_NUM, LRC_NUM_TOTAL, LRC_NUM) )


class ThreadMonitor(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.th_name = self.getName()
        vprint('fork %s to monitor progress ...' % self.th_name)

    def run(self):
        """write lrc into db"""
        while True:
            sleep(2)
            display()


if __name__ == '__main__':

    # process options
    parse = OptionParser()
    parse.add_option("-i", "--input", dest="input", action="store", default="songs_list", 
        help="specify input songs list file")
    parse.add_option("-o", "--output", dest="output", action="store", default="lrc",
        help="specify output lrc file")
    parse.add_option("-t", "--thread_num", type="int", dest="thread_num", action="store", default=8,
        help="specify download threads num")
    parse.add_option("-p", "--parse_thread_num", type="int", dest="parse_thread_num", action="store", default=8,
        help="specify parse threads num")
    parse.add_option("-v", "--verbose", dest="verbose", action="store_true", default=False,
        help="print verbose info")
    parse.add_option("-d", "--debug", dest="debug", action="store_true", default=False,
        help="print debug info")
    (options, args) = parse.parse_args()

    SONG_LIST_FILE = options.input 
    LRC_FILE = options.output
    DOWNLOAD_THREAD_NUM = options.thread_num
    DATAMINE_THREAD_NUM = options.parse_thread_num
    DEBUG = options.debug
    VERBOSE = options.verbose


    # register threads
    threads = []

    threads.append(ThreadFillSong() )
    threads.append(ThreadWriteLrc() )
    threads.append(ThreadMonitor() )

    for i in range(DATAMINE_THREAD_NUM):
        threads.append(ThreadDatamine() )

    for i in range(DOWNLOAD_THREAD_NUM):
        threads.append(ThreadDownload() )

    for th in threads:
        th.setDaemon(True)
        #!! start method will invole run
        th.start()


    # exit until song_num equals lrc_num
    while True:
        sleep(0.1)
        if SONG_NUM == LRC_NUM_TOTAL:
            break

    display()
    print 'done'
