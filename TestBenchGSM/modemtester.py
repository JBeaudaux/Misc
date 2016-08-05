#!/usr/bin/env python

"""ModemTest: Software designed to perform PAD-12 modem"""
__author__ ="Mouhamed NDIAYE"
__version__ = "0.1"
__email__ = "mouhamed.ndiaye@schiller.fr"


from ModemTest import ModemTest

import sys, os, serial, time
from threading import Thread, Timer, Lock

#import Tkinter
import guiModem


def setThreadsLinks(modemClass, displayClass):
	modemClass.setDisplay(displayClass)
	displayClass.setModem(modemClass)

def display():
	#Start the GUI
	myDisplay.mainloop()

def connect(modemClass, port):
	#myModem = ModemTest()
	modemClass.launchModemTest(serial_port)


if __name__ == '__main__':
	if len(sys.argv) < 1:
		print 'Usage: python modemtest.py ttyXXXX [options]'
		sys.exit(-1)

	serial_port = sys.argv[1]
	if len(sys.argv) >= 2:
		print '\n       Modem Test Started\n'
		print '==============================\n'


		myDisplay = guiModem.windowControl(None, 0)
		myModem = ModemTest()
		setThreadsLinks(myModem, myDisplay)

		#Use a separate thread for modem comm
		modemThread = Thread(target=connect, args=[myModem, serial_port])
		modemThread.start()

		display()

