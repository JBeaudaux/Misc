#!/usr/bin/env python

"""ModemTest: Schiller GSM testbench"""
__author__ ="Julien Beaudaux"
__version__ = "2.0"
__email__ = "julien.beaudaux@schiller.fr"


from protocolModem import ModemProto

import sys, os, serial, time
from threading import Thread, Timer, Lock

#import Tkinter
import guiModem
import noGui

import argparse


def setThreadsLinks(modemClass, displayClass):
	modemClass.setDisplay(displayClass)
	displayClass.setModem(modemClass)


def display():
	#Start the GUI
	myDisplay.mainloop()


def connect(modemClass, port, mindelay, version):
	#myModem = ModemProto()
	modemClass.launchModemProto(port, mindelay, version)


if __name__ == '__main__':
	print '\n       Modem Test Started\n'
	print '==============================\n'

	parser = argparse.ArgumentParser(description='Process some integers.')

	parser.add_argument('--serialPort', help='Serial port to use for modem communication (Default : /dev/ttyUSB0)')
	parser.add_argument('--noGUI', action='store_true', help='Launches the program in console mode.')
	parser.add_argument('--reqDelay', help='Sets the minimum delay in ms seperating two frames transmissions (Default : 300ms)')

	args = parser.parse_args()

	if args.serialPort == None:
		args.serialPort = "/dev/ttyUSB0"

	if args.reqDelay == None:
		args.reqDelay = 0.3 #300ms		

	if args.noGUI:
		noDisplay = noGui.noGUI()
		myModem = ModemProto()
		setThreadsLinks(myModem, noDisplay)
		connect(myModem, args.serialPort, args.reqDelay, __version__)
	else:
		myDisplay = guiModem.windowControl(None, __version__)
		myModem = ModemProto()
		setThreadsLinks(myModem, myDisplay)

		#Use a separate thread for modem comm
		modemThread = Thread(target=connect, args=[myModem, args.serialPort, args.reqDelay, __version__])
		modemThread.start()

		display()

	sys.exit(-1)