# *************************************************** 
#   This is an example program for
#   a Word Clock using Raspberry Pi B+, Waveshare ePaper Display and ProtoStax enclosure
#   --> https://www.waveshare.com/product/modules/oleds-lcds/e-paper/2.7inch-e-paper-hat-b.htm
#   --> https://www.protostax.com/products/protostax-for-raspberry-pi-b
#
#   It displays the current time on the Pi as a Word Clock on the ePaper display.
#   It refreshes the clock every 5 minutes and updates the display (as the word
#   clock's granularity is 5 minutes or greater)
 
#   Written by Sridhar Rajagopal for ProtoStax.
#   BSD license. All text above must be included in any redistribution
# *


# Based on Word Clock by Terry Spitz with modifications and adaptation for 2.7in tri-color display
# - centering and padding for 2.7in display, as well as test mode and Ctrl-C/error handling, and
# reorganizing code base to be more modular
#
# Terry Spitz 2018
# word clock for waveshare ePaper
# based on https://github.com/mattohagan/word-clock/blob/master/word_clock.py

# DF - Modify for Waveshare 240x240 LCD PiHat


import sys
sys.path.append(r'lib')

#if sys.version_info[0] < 3:
#    raise Exception("Please use Python 3!")

from enum import Enum
import signal
import epd2in7b
import epdconfig
# Added
import spidev as SPI
import ST7789
import time

from PIL import Image,  ImageDraw,  ImageFont
from datetime import datetime
from time import sleep

s1 = 'IT IS HALFTEN'
s2 = 'QUARTERTWENTY'
s3 = 'FIVE  MINUTES'
s4 = 'PAST     TO  '
s5 = 'ONE TWO THREE'
s6 = 'FOURFIVESEVEN'
s7 = 'SIXEIGHT NINE'
s8 = 'TENELEVENAMPM'
s9 = 'TWELVE OCLOCK'

words = [s1, s2, s3, s4, s5, s6, s7, s8, s9]

# Note:
# The dimensions of the 2.7 in ePaper display are
# 274 x 176

# Note DF:
# The dimensions of the 1.3 in ePaper display are
# 240 x 204

class Clock(object):
    class State(Enum):
        GRAY = 0
        HIGHLIGHT = 1
    def __init__(self):
        self.clear_all()

    def clear_all(self):
        self.itis=Clock.State.GRAY
        self.half=Clock.State.GRAY
        self.ten1=Clock.State.GRAY
        self.quarter=Clock.State.GRAY
        self.twenty=Clock.State.GRAY
        self.five1=Clock.State.GRAY
        self.minutes=Clock.State.GRAY
        self.past=Clock.State.GRAY
        self.to=Clock.State.GRAY
        self.one=Clock.State.GRAY
        self.two=Clock.State.GRAY
        self.three=Clock.State.GRAY
        self.four=Clock.State.GRAY
        self.five2=Clock.State.GRAY
        self.six=Clock.State.GRAY
        self.seven=Clock.State.GRAY
        self.eight=Clock.State.GRAY
        self.nine=Clock.State.GRAY
        self.ten2=Clock.State.GRAY
        self.eleven=Clock.State.GRAY
        self.twelve=Clock.State.GRAY
        self.am=Clock.State.GRAY
        self.pm=Clock.State.GRAY
        self.oclock=Clock.State.GRAY

    def highlight_words(self, hour, minute):
        self.itis = Clock.State.HIGHLIGHT

        # highlight minutes
        if minute >= 55:
            self.five1 = Clock.State.HIGHLIGHT
            self.minutes = Clock.State.HIGHLIGHT
            self.to = Clock.State.HIGHLIGHT
            hour += 1
        elif minute >= 50:
            self.ten1 = Clock.State.HIGHLIGHT
            self.minutes = Clock.State.HIGHLIGHT
            self.to = Clock.State.HIGHLIGHT
            hour += 1
        elif minute >= 45:
            self.quarter = Clock.State.HIGHLIGHT
            self.to = Clock.State.HIGHLIGHT
            hour += 1
        elif minute >= 40:
            self.twenty = Clock.State.HIGHLIGHT
            self.minutes = Clock.State.HIGHLIGHT
            self.to = Clock.State.HIGHLIGHT
            hour += 1
        elif minute >= 30:
            self.half = Clock.State.HIGHLIGHT
            self.past = Clock.State.HIGHLIGHT
        elif minute >= 25:
            self.twenty = Clock.State.HIGHLIGHT
            self.five1 = Clock.State.HIGHLIGHT
            self.minutes = Clock.State.HIGHLIGHT
            self.past = Clock.State.HIGHLIGHT
        elif minute >= 20:
            self.twenty = Clock.State.HIGHLIGHT
            self.minutes = Clock.State.HIGHLIGHT
            self.past = Clock.State.HIGHLIGHT
        elif minute >= 15:
            self.quarter = Clock.State.HIGHLIGHT
            self.past = Clock.State.HIGHLIGHT
        elif minute >= 10:
            self.ten1 = Clock.State.HIGHLIGHT
            self.minutes = Clock.State.HIGHLIGHT
            self.past = Clock.State.HIGHLIGHT
        elif minute >= 5:
            self.five1 = Clock.State.HIGHLIGHT
            self.minutes = Clock.State.HIGHLIGHT
            self.past = Clock.State.HIGHLIGHT
        elif minute >= 0:
            self.oclock = Clock.State.HIGHLIGHT

        # hours
        if hour == 1 or hour == 13:
            self.one = Clock.State.HIGHLIGHT
        elif hour == 2 or hour == 14:
            self.two = Clock.State.HIGHLIGHT
        elif hour == 3 or hour == 15:
            self.three = Clock.State.HIGHLIGHT
        elif hour == 4 or hour == 16:
            self.four = Clock.State.HIGHLIGHT
        elif hour == 5 or hour == 17:
            self.five2 = Clock.State.HIGHLIGHT
        elif hour == 6 or hour == 18:
            self.six = Clock.State.HIGHLIGHT
        elif hour == 7 or hour == 19:
            self.seven = Clock.State.HIGHLIGHT
        elif hour == 8 or hour == 20:
            self.eight = Clock.State.HIGHLIGHT
        elif hour == 9 or hour == 21:
            self.nine = Clock.State.HIGHLIGHT
        elif hour == 10 or hour == 22:
            self.ten2 = Clock.State.HIGHLIGHT
        elif hour == 11 or hour == 23:
            self.eleven = Clock.State.HIGHLIGHT
        elif hour == 12 or hour == 24 or hour == 0:
            self.twelve = Clock.State.HIGHLIGHT

        # am/pm/oclock
        if hour > 12:
            self.pm = Clock.State.HIGHLIGHT
        elif hour == 12:
            self.oclock = Clock.State.HIGHLIGHT
        else:
            self.am = Clock.State.HIGHLIGHT       
        

class Display(object):
    def __init__(self, imageWidth, imageHeight):
        self.imageWidth = imageWidth
        self.imageHeight = imageHeight

        self.clock = Clock()

        
        # xstart and ystart are used to pad and center the text
        # text is started from (width, height) of a character,
        # and so xstart is negative to bring it closer to left
        # of screen
        self.xstart = -10
        self.ystart = -25
        
        # Important!!!
        # Using a Monospace font - this is useful in keeping the width of each
        # line of text of the clock uniform, and all the space adjustments
        # are made using this fact - i.e multiples of a character width or height
        # If you use a different font, remember to adjust the x, y coordinates of the
        # text appropriately
    
        self.font = ImageFont.truetype('fonts/FreeMonoBold.ttf', 28)        

    # Helper methods to draw the word clock
    # GRAY color gets drawn to red
    # HIGHLIGHT color gets drawn to black

    # drawOutline is similar, except that it
    # draws GRAY text in black outline, and
    # HIGHLIGHT text in red
    # Just a different look is all, and you
    # get to see how to write out the font in
    # outline

    def draw(self, idg, idh, w,h,state, text):
        w = w + self.xstart 
        h = h + self.ystart
        if state == Clock.State.GRAY: 
            idg.text((w, h), text, font=self.font, fill="GRAY")
        if state == Clock.State.HIGHLIGHT:
            idh.text((w,h), text, font=self.font, fill="WHITE")
            print(text)

    def drawOutline(self, idg, idh, w,h,state, text):
        w = w + self.xstart 
        h = h + self.ystart    
        if state == Clock.State.GRAY:
            # outline text
            idg.text((w - 1, h), text, font=self.font, fill=0)
            idg.text((w + 1, h), text, font=self.font, fill=0)
            idg.text((w, h - 1), text, font=self.font, fill=0)
            idg.text((w, h + 1), text, font=self.font, fill=0)
            # idg.text((w - 1, h - 1), text, font=self.font, fill=0)
            # idg.text((w + 1, h - 1), text, font=self.font, fill=0)
            # idg.text((w - 1, h + 1), text, font=self.font, fill=0)
            # idg.text((w + 1, h + 1), text, font=self.font, fill=0)
            
            idg.text((w, h), text, font=self.font, fill=1)
        if state == Clock.State.HIGHLIGHT:
            idh.text((w,h), text, font=self.font, fill=0)
            print(text)


    def drawClock(self,hour, minute):
        # reset all. After this we'll figure out which
        # words we want to highlight later on
        self.clock.clear_all()
        self.clock.highlight_words(hour, minute)

        #imageHighlight = Image.new('1', (self.imageWidth, self.imageHeight), 255)    # 1: clear the frame
        #imageGray = Image.new('1', (self.imageWidth, self.imageHeight), 255) # 1: clear the frame       
        imageHighlight = Image.new('RGB', (self.imageWidth, self.imageHeight), "BLACK")    # 1: clear the frame
        imageGray = Image.new('RGB', (self.imageWidth, self.imageHeight), "BLACK") # 1: clear the frame       

        idh = ImageDraw.Draw(imageHighlight)
        idg = ImageDraw.Draw(imageGray)        

        # Here is the use for the Monospace font
        # All calculations are done based on string length and
        # the fact that each character size is the same
        
        width, height = self.font.getsize('Q')
        #print width, height
        #Why not just flipping use the width/height with number of letters/rows???
        #width = self.imageWidth / len(s2)
        #height = self.imageHeight / 9
        print width, height

        height = height - 1 # reduce it a bit to occupy less vertical space

        # first row
        self.draw(idg, idh, width, height,self.clock.itis, text=words[0][:5])
        self.draw(idg, idh, width * 7, height,self.clock.half ,text=words[0][6:10])
        self.draw(idg, idh, width * 11, height,self.clock.ten1 , text=words[0][10:])
        # second row
        self.draw(idg, idh, width, height * 2,self.clock.quarter , text=words[1][:7])
        self.draw(idg, idh, width * 8, height * 2,self.clock.twenty , text=words[1][7:])
        # third row
        self.draw(idg, idh, width, height * 3,self.clock.five1 , text=words[2][:4])
        self.draw(idg, idh, width * 7, height * 3,self.clock.minutes , text=words[2][6:])
        # fourth row
        self.draw(idg, idh, width, height * 4,self.clock.past , text=words[3][:4])
        self.draw(idg, idh, width * 10, height * 4,self.clock.to, text=words[3][9:])
        # fifth row
        self.draw(idg, idh, width, height * 5,self.clock.one , text=words[4][:3])
        self.draw(idg, idh, width * 5, height * 5,self.clock.two , text=words[4][4:7])
        self.draw(idg, idh, width * 9, height * 5,self.clock.three , text=words[4][8:])
        # sixth row
        self.draw(idg, idh, width, height * 6,self.clock.four , text=words[5][:4])
        self.draw(idg, idh, width * 5, height * 6,self.clock.five2 , text=words[5][4:8])
        self.draw(idg, idh, width * 9, height * 6,self.clock.seven , text=words[5][8:])
        # seventh row
        self.draw(idg, idh, width, height * 7,self.clock.six , text=words[6][:3])
        self.draw(idg, idh, width * 4, height * 7, self.clock.eight , text=words[6][3:9])
        self.draw(idg, idh, width * 10, height * 7,self.clock.nine , text=words[6][9:])
        # eigth row
        self.draw(idg, idh, width, height * 8,self.clock.ten2 , text=words[7][:3])
        self.draw(idg, idh, width * 4, height * 8,self.clock.eleven , text=words[7][3:9])
        self.draw(idg, idh, width * 10, height * 8,self.clock.am , text=words[7][9:11])
        self.draw(idg, idh, width * 12, height * 8, self.clock.pm , text=words[7][11:])
        # ninth row
        self.draw(idg, idh, width, height * 9,self.clock.twelve , text=words[8][:6])
        self.draw(idg, idh, width * 8, height * 9,self.clock.oclock , text=words[8][7:])

        # extra letters
        self.draw(idg, idh, width * 3, height, Clock.State.GRAY, text='V  T')
        self.draw(idg, idh, width * 5, height * 3, Clock.State.GRAY, text='GO')
        self.draw(idg, idh, width * 5, height * 4, Clock.State.GRAY, text='NOLES  MO')
        self.draw(idg, idh, width * 4, height * 5, Clock.State.GRAY, text='S   C')
        self.draw(idg, idh, width * 9, height * 7, Clock.State.GRAY, text='Z')
        self.draw(idg, idh, width * 7, height * 9, Clock.State.GRAY, text='P')

        imageGray=imageGray.transpose(Image.ROTATE_180)
        imageHighlight=imageHighlight.transpose(Image.ROTATE_180)
        imageLCD = Image.blend(imageHighlight,imageGray,0.33)     

        return imageHighlight, imageGray, imageLCD

# The main function    

def main():

    """
    # Commented out for new display type DF

    # Initialize and clear the 2in7b (tri-color) display
    epd = epd2in7b.EPD()
    epd.init()
    epd.Clear()

    display = Display(epd2in7b.EPD_WIDTH, epd2in7b.EPD_HEIGHT)

    """

    # Raspberry Pi pin configuration:
    RST = 27
    DC = 25
    BL = 24
    bus = 0 
    device = 0 

    # 240x240 display with hardware SPI:
    disp = ST7789.ST7789(SPI.SpiDev(bus, device),RST, DC, BL)

    # Call 'Display' sub with Waveshare sizes
    display = Display(disp.width,disp.height)
   
    # Initialize library.
    disp.Init()

    # Clear display.
    disp.clear()


    while(True):
        #epd.init()
        disp.Init()

        # check time.
        # You can specify "hour minute second" as command-line arguments
        # to be in "test-mode". It will run once in test mode with the
        # time specified and then quit
        hour = None
        minute = None
        second = None

        if (len(sys.argv) > 1): 
            hour = int(sys.argv[1])
            minute = int(sys.argv[2])
            second = int(sys.argv[3])
        else:
            now = datetime.now()
            hour = now.hour
            minute = now.minute
            second = now.second

        #print("Time is {}:{}:{}".format(hour, minute, second))

        #Call sub to create clock image
        (imageHighlight, imageGray, imageLCD) = display.drawClock(hour, minute)

        # Display image on device

        # We're mapping the highlighted text to black and the gray text to red
        #Display on epaper
        #epd.display(epd.getbuffer(imageHighlight), epd.getbuffer(imageGray))

        #Display on LCD
        disp.ShowImage(imageLCD,0,0)

        #Debug write to file
        imageLCD = imageLCD.transpose(Image.ROTATE_180)
        imageLCD.save("imageLCD.png")

        #Wait
        sleep(2)
        #epd.sleep()
       
        if (len(sys.argv) > 1):
            # If we are running with command line arguments, we are in "test-mode"
            # We run with the time specified on the command line and then just
            # exit
            exit() #debugging with command line arguments, so just exit after one run
        else:
            # Go to sleep until the next time to wake up and display the time again
            # Since the word clock has a granularity of 5 minutes or greater, we can
            # go to sleep for 5 minutes
            sleep(300) # sleep for 5 minutes because that is the granularity of the word clock!


# gracefully exit without a big exception message if possible
def ctrl_c_handler(signal, frame):
    print('Goodbye!')
    # XXX : TODO
    #
    # To preserve the life of the ePaper display, it is best not to keep it powered up -
    # instead putting it to sleep when done displaying, or cutting off power to it altogether.
    #
    # epdconfig.module_exit() shuts off power to the module and calls GPIO.cleanup()
    # The latest epd library chooses to shut off power (call module_exit) even when calling epd.sleep()    
    # epd.sleep() calls epdconfig.module_exit(), which in turns calls cleanup().
    # We can therefore end up in a situation calling GPIO.cleanup twice
    # 
    # Need to cleanup Waveshare epd code to call GPIO.cleanup() only once
    # for now, calling epdconfig.module_init() to set up GPIO before calling module_exit to make sure
    # power to the ePaper display is cut off on exit
    # I have also modified epdconfig.py to initialize SPI handle in module_init() (vs. at the global scope)
    # because slepe/module_exit closes the SPI handle, which wasn't getting initialized in module_init
    #epdconfig.module_init()
    #epdconfig.module_exit()
    disp.Init()
    disp.clear() 

    print("Remember to clear the display using cleardisplay.py if you plan to power down your Pi and store it, to prevent burn-in!")
    exit(0)

signal.signal(signal.SIGINT, ctrl_c_handler)


if __name__ == '__main__':
    main()
