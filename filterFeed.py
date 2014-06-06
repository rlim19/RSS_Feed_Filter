#! /usr/bin/env python
# -*- coding: utf-8 -*-

# RSS Feed Filter

import feedparser
import string
import time
from project_util import translate_html
from news_gui import Popup

#======================
# Code for retrieving and parsing
# Google and Yahoo News feeds
# Do not change this code
#======================

def process(url):
    """
    Fetches news items from the rss url and parses them.
    Returns a list of NewsStory-s.
    """
    feed = feedparser.parse(url)
    entries = feed.entries
    ret = []
    for entry in entries:
        guid = entry.guid
        title = translate_html(entry.title)
        link = entry.link
        summary = translate_html(entry.summary)
        try:
            subject = translate_html(entry.tags[0]['term'])
        except AttributeError:
            subject = ""
        newsStory = NewsStory(guid, title, subject, summary, link)
        ret.append(newsStory)
    return ret

#======================
# Part 1
# Data structure design
#======================

class NewsStory(object):
    def __init__(self, guid, title, subject, summary, link):
        self.guid = guid
        self.title = title
        self.subject = subject
        self.summary = summary
        self.link = link
    def get_guid(self):
        return self.guid
    def get_title(self):
        return self.title
    def get_subject(self):
        return self.subject
    def get_summary(self):
        return self.summary
    def get_link(self):
        return self.link

#======================
# Part 2
# Triggers
#======================

class Trigger(object):
    def evaluate(self, story):
        """
        Returns True if an alert should be generated
        for the given news item, or False otherwise.
        """
        raise NotImplementedError

class WordTrigger(Trigger):
    def __init__(self, word):
        self.word = word.lower()

    def is_word_in(self, text):

        wordStory = text.lower()
        # clean word from punctuation
        for punct in string.punctuation:
            if punct in wordStory:
                wordStory = wordStory.replace(punct, ' ')
        wordStory = wordStory.split(' ')
        
        if self.word in wordStory:
            return True
        else:
            return False

class TitleTrigger(WordTrigger):
    def __init__(self, word):
        WordTrigger.__init__(self,word)

    def evaluate(self, story):
        if WordTrigger.is_word_in(self, story.get_title()):
            return True
        else:
            return False

class SubjectTrigger(WordTrigger):
    def __init__(self, word):
        WordTrigger.__init__(self,word)

    def evaluate(self, story):
        if WordTrigger.is_word_in(self, story.get_subject()):
            return True
        else:
            return False

class SummaryTrigger(WordTrigger):
    def __init__(self, word):
        WordTrigger.__init__(self,word)

    def evaluate(self, story):
        if WordTrigger.is_word_in(self, story.get_summary()):
            return True
        else:
            return False

# Composite Triggers
class NotTrigger(Trigger):
    def __init__(self, trigger):
        self.trigger = trigger
    def evaluate(self, story):
        return not (self.trigger.evaluate(story))

class AndTrigger(Trigger):
    def __init__(self, trigger1, trigger2):
        self.trigger1 = trigger1
        self.trigger2 = trigger2
    def evaluate(self, story):
        return self.trigger1.evaluate(story) and \
               self.trigger2.evaluate(story) 

class OrTrigger(Trigger):
    def __init__(self, trigger1, trigger2):
        self.trigger1 = trigger1
        self.trigger2 = trigger2
    def evaluate(self, story):
        return self.trigger1.evaluate(story) or \
               self.trigger2.evaluate(story) 

class PhraseTrigger(Trigger):
    def __init__(self, phrase):
        self.phrase = phrase

    def evaluate(self, story):
        return self.phrase in story.get_title() or \
               self.phrase in story.get_summary() or \
               self.phrase in story.get_subject() 
                
#======================
# Part 3
# Filtering
#======================

def filter_stories(stories, triggerlist):
    """
    Takes in a list of NewsStory-s.
    Returns only those stories for whom
    a trigger in triggerlist fires.
    """

    filtered_stories = []
    for story in stories:
        for trigger in triggerlist:
            if trigger.evaluate(story):
                filtered_stories.append(story)

    return filtered_stories

#======================
# Part 4
# User-Specified Triggers
#======================

def createTrigger(trigger_dict, trigger_type, trigger_args, name):
    """
    Output: trigger instance in a modified trigger_dict
        * e.g : AndTrigger, SummaryTrigger added to the trigger_dict
    Input:
     - trigger_dict:
        * key   = name of trigger instance 
        * value = trigger instance
     - trigger_type (class type)
        * e.g = 'SUMMARY'
     - trigger_args = parameters for the trigger(class) constructor
        * e.g = ["Brazil"], ["t2", "t3"] --> for NOT, OR and AND
     - name = name of trigger instance
    """

    if trigger_type == 'TITLE':
        trigger = TitleTrigger(trigger_args[0])
    elif trigger_type == 'SUBJECT':
        trigger = SubjectTrigger(trigger_args[0])
    elif trigger_type == 'SUMMARY':
        trigger = SummaryTrigger(trigger_args[0])
    elif trigger_type == 'NOT':
        trigger = NotTrigger(trigger_dict[trigger_args[0]]) 
    elif trigger_type == 'AND':
        trigger = AndTrigger(trigger_dict[trigger_args[0]], 
                             trigger_dict[trigger_args[1]])
    elif trigger_type == 'OR':
        trigger = OrTrigger(trigger_dict[trigger_args[0]], 
                             trigger_dict[trigger_args[1]])
    elif trigger_type == 'PHRASE':
        trigger = PhraseTrigger(' '.join(trigger_args))
    else:
        return None

    trigger_dict[name] = trigger



def readTriggerConfig(filename):
    """
    Returns a list of trigger objects
    that correspond to the rules set
    in the file filename
    """

    with open(filename) as configFile:
        trigger_lines = []
        for line in configFile:
            line = line.rstrip().split(' ')
            if line[0] == '' or line[0] == '#':
                continue
            else:
                trigger_lines.append(line)

    triggers = []
    trigger_dict = {}
    for trigger_line in trigger_lines:
        if trigger_line[0] != "ADD":
            trigger = createTrigger(trigger_dict, trigger_line[1],
                                    trigger_line[2:], trigger_line[0])

        else:
            for name in trigger_line[1:]:
                triggers.append(trigger_dict[name])

    return triggers


    
import thread

def main_thread(p):

    # read from the config file
    triggerlist = readTriggerConfig("triggers.txt")

    guidShown = []
    
    while True:
        print "Polling..."

        # Get stories from Google's Top Stories RSS news feed
        stories = process("http://news.google.com/?output=rss")
        # Get stories from Yahoo's Top Stories RSS news feed
        stories.extend(process("http://rss.news.yahoo.com/rss/topstories"))

        # Only select stories we're interested in
        stories = filter_stories(stories, triggerlist)
    
        # Don't print a story if we have already printed it before
        newstories = []
        for story in stories:
            if story.get_guid() not in guidShown:
                newstories.append(story)
        
        for story in newstories:
            guidShown.append(story.get_guid())
            p.newWindow(story)

        print "Sleeping..."
        time.sleep(SLEEPTIME)

SLEEPTIME = 60 #seconds -- how often we poll
if __name__ == '__main__':
    p = Popup()
    thread.start_new_thread(main_thread, (p,))
    p.start()
