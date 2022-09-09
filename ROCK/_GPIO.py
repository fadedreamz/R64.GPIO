from ROCK.GPIOBase import *

handle = GPIOBase.GPIOFactory('ROCK64')


def setmode(mode):
    handle.setmode(mode)
    pass


def getmode():
    handle.getmode()
    pass


def setwarnings(state=True):
    handle.setwarnings(state)
    pass


def setup(channel, direction, pull_up_down=PUD_DOWN, initial=LOW):
    handle.setup(channel, direction, pull_up_down, initial)
    pass


def output(channel, value):
    return handle.output(channel, value)


def add_event_detect(channel, edge, callback, bouncetime = 1):
    return handle.add_event_detect(channel, edge, callback, bouncetime)


def remove_event_detect(channel):
    return handle.remove_event_detect(channel)


def input(channel):
    return handle.input(channel)
