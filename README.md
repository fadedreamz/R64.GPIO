# ROCK.GPIO
A clone of RPi.GPIO library for Rock64
Inspired by Leapo's clone (https://github.com/Leapo/Rock64-R64.GPIO). Reimplementing due to licensing issue.

Goal: 
 - minimal modification from RPi.GPIO
  - as 'pythonicly' efficient it can be
  - easy migration to other boards

It can be easily ported for other PINE boards as well, for example Rock64Pro.(But I only have Rock64 atm)

Following functionalities are implemented and tested on rock64

| Function  | Support  | Notes  |
|-----------|----------|--------|
| GPIO.setmode()  |  Yes  |  BCM does not check for pins that are disabled when MicroSD is in use  |
| GPIO.setwarnings() | YES | |
| GPIO.setup() | Partial (Pull UP/DOWN ignored) | Default Pull UP/DOWN used |
| GPIO.output() | YES | |
| GPIO.input() | YES | |
| GPIO.cleanup() | Not yet implemented | |
| GPIO.PWM() | Not yet implemented | |
| GPIO.wait_for_edge() | Not yet implemented | |
| GPIO.event_detect() | Not yet implemented | |
| GPIO.add_event_detect() | YES | epoll() has a timeout of 5 seconds to allow graceful cleanup via GPIO.remove_event_detect(), you can adjust it accordingly to match your desired performance|
| GPIO.remove_event_detect() | YES | depends upon the epoll() timeout, if epoll() has infinite timeout, calling this function will deadlock |
| Pull UP/Down Selection | Not yet Implemented | atm moment I don't need it, but I will include this if I have some time, R&D required |
| Hardware PWM | Not yet implemented | rk3328 does have hardware PWM, I think we can use them to yield better performance |
| Software PWM through C library | Not yet implemented | Python GC is unreliable when it comes to timing, hence it is better to implement it in C and interface to python|
| Documentation | On going | ;-) |

Disclaimer: I do not have complete knowledge of RPi.GPIO (infact never used it), but I needed a Python library
for Rock64 while moving a product from RPi to Rock64. If you have any suggestions, let me know.
