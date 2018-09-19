import ROCK.GPIO as GPIO
import time
from threading import Thread

keep_blinking = True

def test_gpio_output():
    GPIO.setmode(GPIO.PINLAYOUT.ROCK64)
    GPIO.setwarnings(state=True)
    GPIO.setup("GPIO1_A3", GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup("GPIO1_A6", GPIO.IN, initial=GPIO.HIGH)
    GPIO.add_event_detect("GPIO1_A6", GPIO.RISING, start_blink, 500)
    input()
    GPIO.remove_event_detect("GPIO1_A6")
    #global keep_blinking
    #keep_blinking = False
    input()


def start_blink(channel, state):
    print('Got State = {} on PIN {}'.format(state, channel))
    #t = Thread(target=blink, )
    #t.start()
    #t.join()

def blink():
    while keep_blinking:
        GPIO.output("GPIO1_A3", GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output("GPIO1_A3", GPIO.LOW)
        time.sleep(0.5)


if __name__ == '__main__':
    test_gpio_output()