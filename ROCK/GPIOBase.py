from abc import ABC, abstractmethod
from enum import Enum
from ROCK.Rock64Configs import BaseConfig
import sys
import os
import select
from threading import Thread
import time

ROCK64 = 'ROCK64'
BOARD = 'BOARD'
BCM = 'BCM'


IN = "in"
OUT = "out"

NONE = "none"
RISING = "rising"
FALLING = "falling"
BOTH = "both"

HIGH, LOW = BaseConfig.factory('ROCK64').get_highlow()

PUD_UP, PUD_DOWN = BaseConfig.factory('ROCK64').get_pullupdown()

class GPIOBase(ABC):

    warning_enabled = False
    mode = None

    @abstractmethod
    def setmode(self, mode):
        pass

    def getmode(self):
        return self.mode

    def setwarnings(self, state=True):
        self.warning_enabled = state
        pass

    @abstractmethod
    def setup(self, channel, direction, pull_up_down=PUD_DOWN, initial=LOW):
        pass

    @abstractmethod
    def input(self, channel):
        pass

    @abstractmethod
    def output(self, channel, value):
        pass

    @abstractmethod
    def add_event_detect(self, channel, edge, callback, bouncetime):
        pass

    @abstractmethod
    def remove_event_detect(self, channel):
        pass

    @staticmethod
    def GPIOFactory(target):
        if target == 'ROCK64':
            return GPIORock64()
        else:
            raise ValueError("Not supported : {}".format(target))


class ThreadContext(object):
    closethread = False
    bouncetime = None
    cb = None
    threadhandle = None

    def __init__(self, cb, bouncetime):
        self.cb = cb
        self.bouncetime = bouncetime
        self.closethread = False

    def notify_close(self):
        self.closethread = True
        if self.threadhandle is not None:
            self.threadhandle.join()

class GPIORock64(GPIOBase):
    gpio_offset = 0
    event_cbs = {}
    valid_channels = [27, 32, 33, 34, 35, 36, 37, 38, 64, 65, 67, 68, 69, 76, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 96, 97, 98, 100, 101, 102, 103, 104]
    # http://files.pine64.org/doc/rock64/ROCK64_Pi-2%20_and_Pi_P5+_Bus.pdf
    native_to_rock64_map = [None, None, "GPIO2_D1", None, "GPIO2_D0", None, None, "GPIO2_A0", None, "GPIO2_A1",
                            None, "GPIO2_A3", None, None, "GPIO3_A4", "GPIO3_A5", None, "GPIO3_A6", "GPIO3_A1", None,
                            "GPIO3_A2", "GPIO3_A7", "GPIO3_A0", "GPIO3_B0", None, "GPIO2_B4", "GPIO2_A4", "GPIO2_A5", None, None,
                            None, "GPIO1_A6", "GPIO1_A0", None, "GPIO1_A1", "GPIO1_A5", "GPIO1_A2", "GPIO1_A4", None, "GPIO1_A3"]
    # Used Pi2 Header Pinout for comparison and pin-number reference - https://cdn.sparkfun.com/assets/learn_tutorials/4/2/4/header_pinout.jpg
    bcm_to_rock64_map = [None,                                                       # 0
                         None, 'GPIO2_D1', 'GPIO2_D0', 'GPIO2_D4', None,             # 1-5 - No GPIO 01 on RPi - GPIO 05 not connected on R64
                         None, 'GPIO2_B4', 'GPIO3_B0', 'GPIO3_A1', 'GPIO3_A2',       # 6-10 - GPIO 06 not connected on R64
                         None, 'GPIO1_A6', 'GPIO1_A0', 'GPIO2_A0', 'GPIO2_A1',       # 11-15 - No GPIO 11 on RPi
                         'GPIO1_A5', None, 'GPIO2_A3', 'GPIO1_A1', 'GPIO1_A4',       # 16-20 - GPIO 17 not connected on R64
                         'GPIO1_A3', 'GPIO3_A4', 'GPIO3_A5', 'GPIO3_A6', 'GPIO3_A7', # 21-25
                         'GPIO1_A2', 'GPIO0_A0']                                     # 26-27

    #Note: BCM GPIO - 12, 13, 16, 19, 20, 21, amd 26 are not accesible if onboard MicroSD card reader is in use


    def __init__(self, gpio_offset=0):
        super().__init__()
        self.gpio_offset = gpio_offset
        pass

    def channel_to_pin(self, pin):
        """Converts the given channel to physical pin to be exported via gpio sysfs"""
        pinName = pin
        if self.mode == BOARD:
            pinName = self.board_to_pin(pin)
        elif self.mode == BCM:
            pinName = self.bcm_to_pin(pin)
        elif self.mode == ROCK64:
            pinName = pin
        else:
            raise ValueError("invalid pin and/or mode")
        return self.rock64_to_pin(pinName)

    def bcm_to_pin(self, bcmpin):
        """Converts the given channel (assuming bcm numbering is being used) to physical pin"""
        if not isinstance(bcmpin, int):
            raise ValueError("invalid bcm pin, expected int")
        if bcmpin < 0 or bcmpin >= len(self.bcm_to_rock64_map):
            raise ValueError("invalid bcm pin given, should be within the rage of 0 to {}".format(len(self.bcm_to_rock64_map) - 1))
        if self.bcm_to_rock64_map[bcmpin] is None:
            raise ValueError("invalid board pin, no possible mapping with GPIO pins")
        return self.bcm_to_rock64_map[bcmpin]

    def board_to_pin(self, boardpin):
        """Converts the given channel (assuming board numbering is being used) to physical pin"""
        if not isinstance(boardpin, int):
            raise ValueError("invalid board pin, expected int")
        if boardpin < 0 or boardpin >= len(self.native_to_rock64_map):
            raise ValueError("invalid board pin given, should be within the rage of 0 to {}".format(len(self.native_to_rock64_map) - 1))
        if self.native_to_rock64_map[boardpin] is None:
            raise ValueError("invalid board pin, no possible mapping with GPIO pins")
        return self.native_to_rock64_map[boardpin]

    def rock64_to_pin(self, rock64pin):
        """Converts the given channel (assuming rock64 gpio numbering is being used) to physical pin"""
        if len(rock64pin) != 8:
            print("length of input {} = {}".format(rock64pin, len(rock64pin)))
            raise ValueError("invalid rock64 pin format, should be of GPIO<N>_<C><N> format "
                             "where N is number and C is character")
        if rock64pin[:4] != "GPIO":
            raise ValueError("invalid rock64 pin format, should be of GPIO{1-4}_{A-D}{1-9} format")
        bankNumber = int(rock64pin[4:5])
        padNumber = rock64pin[-2]
        pinNumber = int(rock64pin[-1])
        if padNumber not in ["A", "B", "C", "D"]:
            raise ValueError("invalid rock64 pin format, should be of GPIO{1-4}_{A-D}{1-9} format")
        padNumber = ["A", "B", "C", "D"].index(padNumber)
        channel = self.gpio_offset + (bankNumber * 32) + (8 * padNumber) + pinNumber
        if channel not in self.valid_channels:
            raise ValueError("invalid rock64 pin : {} translates to {}, but not valid for rock64".format(rock64pin, channel))
        return channel

    def setmode(self, mode):
        """Sets the mode for GPIO"""
        if mode not in (ROCK64, BOARD, BCM):
            raise RuntimeError("mode not supported : {}".format(mode))
        self.mode = mode
        pass

    def log_warning(self, msg):
        """Logs the message based on warning settings"""
        if self.warning_enabled:
            print("[WARN] {}".format(msg))

    def export(self, channel):
        base_syspath = "/sys/class/gpio"
        base_export_path = "{}/export".format(base_syspath)
        exported = "{}/gpio{}".format(base_syspath, channel)
        if os.path.exists(exported):  # already exported
            self.log_warning("{} already exported as {}".format(channel, exported))
            return True
        with open(base_export_path, "w") as f:
            f.write(str(channel))
        if os.path.exists(exported):  # export successful
            return True
        return False

    def get_direction(self, channel):
        base_syspath = "/sys/class/gpio"
        base_gpio_direction = "{}/gpio{}/direction".format(base_syspath, channel)
        if not os.path.exists(base_gpio_direction):
            raise ValueError("pin is not exported")
        with open(base_gpio_direction, "r") as f:
            return f.readline().splitlines()[0]  # unsafe, but this is sysfs and the output is fixed

    def set_direction(self, channel, direction):
        base_syspath = "/sys/class/gpio"
        base_gpio_direction = "{}/gpio{}/direction".format(base_syspath, channel)
        if not os.path.exists(base_gpio_direction):
            raise ValueError("channel not exported")
        with open(base_gpio_direction, "w") as f:
            f.write(direction)
        if direction in self.get_direction(channel):
                return True
        return False

    def get_value(self, channel):
        base_syspath = "/sys/class/gpio"
        base_gpio_value = "{}/gpio{}/value".format(base_syspath, channel)
        if not os.path.exists(base_gpio_value):
            raise ValueError("pin is not exported")
        with open(base_gpio_value) as f:
            return int(f.readline())

    def set_value(self, channel, value):
        base_syspath = "/sys/class/gpio"
        base_gpio_value = "{}/gpio{}/value".format(base_syspath, channel)
        if self.get_direction(channel) != OUT:
            return False
        with open(base_gpio_value, "w") as f:
            f.write(value)
        return True

    def get_edge(self, channel):
        base_syspath = "/sys/class/gpio"
        base_gpio_edge = "{}/gpio{}/edge".format(base_syspath, channel)
        if not os.path.exists(base_gpio_edge):
            raise ValueError("pin is not exported")
        with open(base_gpio_edge) as f:
            return f.readline().splitlines()[0]

    def set_edge(self, channel, edge):
        base_syspath = "/sys/class/gpio"
        base_gpio_edge = "{}/gpio{}/edge".format(base_syspath, channel)
        if not os.path.exists(base_gpio_edge):
            raise ValueError("pin is not exported")
        if edge not in [RISING, FALLING, BOTH, NONE]:
            raise ValueError("wrong edge type given")
        with open(base_gpio_edge, 'w') as f:
            f.write(edge)
        return True

    def validate_channel(self, channel):
        if isinstance(channel, list):
            for c in channel:
                self.validate_channel(c)
            return channel
        elif isinstance(channel, int):
            if self.mode != BOARD and self.mode != BCM:
                raise ValueError("invalid channel given, mode is not BOARD or BCM, but channel is integer")
            return [channel]
        elif isinstance(channel, str):
            if self.mode != ROCK64:
                raise ValueError("invalid channel given, mode is not ROCK64, but channel is string")
            return [channel]
        raise ValueError("invalid channel given")

    def setup(self, channel, direction, pull_up_down=PUD_DOWN, initial=LOW):

        channel = self.validate_channel(channel)

        for cur_chn in channel:
            chn_no = self.channel_to_pin(cur_chn)
            if not self.export(chn_no):
                raise ValueError("unable to export {}".format(cur_chn))
            if not self.set_direction(chn_no, direction):
                raise ValueError("unable to set direction {}".format(cur_chn))
            # for now pull_up down is ignored, as I have to double check the datasheet to see if
            # there is any such mode, if you know, please feel free to add them
            if direction == OUT:
                if not self.set_value(chn_no, initial):
                    raise ValueError("unable to set value {}".format(cur_chn))
        pass

    def fn_event_detect(self, channel, ctx):
        if channel not in self.event_cbs.keys():
            self.log_warning("unable to get context for the add_event_function, aborting")

        epoll = select.epoll()
        initial = self.get_value(channel)
        initial_epoc = int(round(time.time() * 1000))
        file = open("/sys/class/gpio/gpio{}/value".format(channel), 'r')
        file.readline()  # clear pending interrupts at the driver level
        file.seek(0)  # reset read cursor
        epoll.register(file.fileno(), select.EPOLLPRI | select.EPOLLERR)
        ctx.pollhandle = epoll
        while not ctx.closethread:
            events = epoll.poll(5)  # poll every 5 seconds
            for fileno, event in events:
                if event & select.EPOLLPRI:
                    value = self.get_value(channel)
                    #print('OLD : {} NEW : {}'.format(initial, value))
                    cur_epoc = int(round(time.time() * 1000))
                    if cur_epoc - initial_epoc >= ctx.bouncetime and initial != value:
                        initial_epoc = cur_epoc
                        ctx.cb(channel, value)
            file.readline()  # clear pending interrupts at the driver level
            file.seek(0)  # reset read cursor
        print("unregistering add_event_detect for {}".format(channel))

    def add_event_detect(self, channel, edge, callback, bouncetime = 1):
        if callback is None:
            self.log_warning("no callback given, ignoring add_event_detect() request")
            return
        if channel in self.event_cbs.keys():
            self.log_warning("a previous event was defined for the key, replacing it")
            ctx = self.event_cbs[channel]
            ctx.notify_close()
            del self.event_cbs[channel]
        channel = self.validate_channel(channel)

        if edge not in [RISING, FALLING, BOTH]:
            raise ValueError("invalid edge value given for event detect. Only RISING, FALLING or BOTH allowed")

        for cur_chn in channel:
            chn_no = self.channel_to_pin(cur_chn)
            self.set_edge(chn_no, edge)
            if self.get_edge(chn_no) != edge:
                raise ValueError("unable to set edge for event detect")
            ctx = ThreadContext(cb=callback, bouncetime=bouncetime)
            ctx.threadhandle = Thread(target=self.fn_event_detect, args=(chn_no, ctx))
            self.event_cbs[chn_no] = ctx
            ctx.threadhandle.start()
        pass

    def remove_event_detect(self, channel):
        channel = self.validate_channel(channel)
        for cur_chn in channel:
            chn_no = self.channel_to_pin(cur_chn)
            if chn_no not in self.event_cbs:
                raise ValueError("invalid channel {} given, no event was registered".format(cur_chn))
            ctx = self.event_cbs[chn_no]
            ctx.notify_close()
            del self.event_cbs[chn_no]

    def input(self, channel):
        self.validate_channel(channel)
        phypin = self.channel_to_pin(channel)
        return self.get_value(phypin)

    def output(self, channel, value):
        self.validate_channel(channel)
        phypin = self.channel_to_pin(channel)
        return self.set_value(phypin, value)
