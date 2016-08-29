#!/usr/bin/env python

# Empty class to disable GUI
class noGUI():

	def __init__(self):
		print "No GUI mode"

	def setModem(self, nothing):
		pass

	# Methods used by the modem to update status
	def Update_Connections(self, ecall, voiceCall, dataCall):
		pass

	def UpdateGPScoordinates(self, lati, longi, satellites):
		pass


	def UpdateGPSstatus(self, status):
		pass


	def UpdatePortion(self, val):
		pass


	def UpdateConsolePrompt(self, text):
		pass
