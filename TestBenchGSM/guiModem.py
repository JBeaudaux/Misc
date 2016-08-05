#!/usr/bin/env python

__version__ = "0.1"

from threading import Timer
import time, math, os, sys

import Tkinter
import ttk

import tkFileDialog
from tkFileDialog import askopenfilename # Open dialog box

import Image, ImageTk

import requests
from StringIO import StringIO


class windowControl(Tkinter.Tk):

	runDemo = 0	#0=inactive ; 1=live ; 2=recorded
	recordDemo = False
	pauseDemo = True

	coord = {'xaxis':0, 'yaxis':0, 'zaxis':0, 'acc':0}

	precision = 0.02	# Time interval between samples (in sec)
	iteration = 0	# Number of iterations from the first sample
	windowSize = 1200

	moyVal = 0
	moySSE = 0
	SSE = 0

	latitudeAnchor = 49.023180
	longitudeAnchor = 7.962005

	longitudeGPS = 0
	latitudeGPS = 0
	satellitesGPS = 0
	movement = 0
	StatusGPS = "Disabled"

	# Define the size of the map
	sizeMapX = 320
	sizeMapY = 320

	ProgressbarVal = 0


	def __init__(self,parent, option=0):
		Tkinter.Tk.__init__(self, parent)
		self.parent = parent
		self.title("FRED PA-1 - GSM demonstrator - V%s"%(__version__))

		self.configPath = ""

		#ico = r"%s/%s/blueprint.gif"%(os.getcwd(), sys.argv[0][:-11])
		#img = Tkinter.Image("photo", file=ico)
		#self.tk.call('wm','iconphoto',self._w,img)

		#self.geometry(600, 300)
		#self.minsize(350, 450)
		#self.maxsize(350, 450)

		self['bg']='white'
		
		self.initialize()
		#self.mesEssais()


	# Sets the GUI up
	def initialize(self):
		#Creates the global view
		#self.canvas = Tkinter.Canvas(self, height=300, width=1200, bg="white")
		#self.canvas.pack(padx=5, pady=5)

		global multilang

		col = 0
		row = 0

		#Group test
		#Mafenetre = Tkinter.Tk()
		#Mafenetre.title('Frame widget')
		#Mafenetre['bg']='bisque' # couleur de fond
		Frame1 = Tkinter.Frame(self, borderwidth=2)

		# Binds the carriage return to a "button pressed" event
		self.bind('<Return>', self.EnterPressed)
		self.protocol("WM_DELETE_WINDOW", self.ActionDisconnect)


		row +=1
		col += 1

		leftGroup = Tkinter.LabelFrame(self, bd=0, bg='white', padx=5, pady=5)
		leftGroup.grid(row=row, column=col)

		rightGroup = Tkinter.LabelFrame(self, bd=0, bg='white', padx=5, pady=5)
		rightGroup.grid(row=row, column=col+1)



		globalGroup = Tkinter.LabelFrame(leftGroup, text="Connection status", bg='white', padx=5, pady=5)
		globalGroup.grid(row=row, column=col)

		statusGroup = Tkinter.LabelFrame(globalGroup, bd=0, bg='white', padx=5, pady=5)
		statusGroup.grid(row=row, column=col)

		tmp = Tkinter.Label(statusGroup, text="E-call status", bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row, column=col)

		tmp = Tkinter.Label(statusGroup, text=" - ", bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row, column=col+1)

		self.ecallText = Tkinter.StringVar()
		self.ecallStatus = Tkinter.Label(statusGroup, textvariable=self.ecallText, bg='white', fg='red', anchor="w", font="Helvetica 14")
		self.ecallStatus.grid(row=row, column=col+2)
		self.ecallText.set("Disconnected")

		row += 1

		tmp = Tkinter.Label(statusGroup, text="Voice call status", bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row, column=col)

		tmp = Tkinter.Label(statusGroup, text=" - ", bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row, column=col+1)

		self.voicecallText = Tkinter.StringVar()
		self.voicecallStatus = Tkinter.Label(statusGroup, textvariable=self.voicecallText, anchor="w", bg='white', fg='red', font="Helvetica 14")
		self.voicecallStatus.grid(row=row, column=col+2)
		self.voicecallText.set("Disconnected")

		row += 1

		tmp = Tkinter.Label(statusGroup, text="Data call status", bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row, column=col)

		tmp = Tkinter.Label(statusGroup, text=" - ", bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row, column=col+1)

		self.datacallText = Tkinter.StringVar()
		self.datacallStatus = Tkinter.Label(statusGroup, textvariable=self.datacallText, anchor="w", bg='white', fg='red', font="Helvetica 14")
		self.datacallStatus.grid(row=row, column=col+2)
		self.datacallText.set("Disconnected")

		row = 2
		col = 1

		self.trackGroup = Tkinter.LabelFrame(leftGroup, text="GPS tracking", bg='white', padx=5, pady=5)
		self.trackGroup.grid(row=row, column=col)

		self.reloadImage(self.getDefiMap(), self.trackGroup)
		self.image_label.grid(row=row, column=col)

		tmpGroup = Tkinter.LabelFrame(self.trackGroup, bd=0, bg='white')
		tmpGroup.grid(row=row+1, column=col)



		tmp = Tkinter.Label(tmpGroup, text="Status", bg='white', anchor="w", font="Helvetica 12")
		tmp.grid(row=row+1, column=col)

		tmp = Tkinter.Label(tmpGroup, text=" - ", bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row+1, column=col+1)

		self.statusGPStext = Tkinter.StringVar()
		self.statusGPStext.set(self.StatusGPS)
		self.trackerStatus = Tkinter.Label(tmpGroup, textvariable=self.statusGPStext, fg='red', bg='white', anchor="w", font="Helvetica 12")
		self.trackerStatus.grid(row=row+1, column=col+2)


		tmp = Tkinter.Label(tmpGroup, text="Latitude", bg='white', anchor="w", font="Helvetica 12")
		tmp.grid(row=row+2, column=col)

		tmp = Tkinter.Label(tmpGroup, text=" - ", bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row+2, column=col+1)

		self.GPSlatitudeText = Tkinter.StringVar()
		self.GPSlatitudeText.set("%f"%(self.latitudeGPS))
		tmp = Tkinter.Label(tmpGroup, textvariable=self.GPSlatitudeText, bg='white', anchor="w", font="Helvetica 12")
		tmp.grid(row=row+2, column=col+2)


		tmp = Tkinter.Label(tmpGroup, text="Longitude", bg='white', anchor="w", font="Helvetica 12")
		tmp.grid(row=row+3, column=col)

		tmp = Tkinter.Label(tmpGroup, text=" - ", bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row+3, column=col+1)

		self.GPSlongitudeText = Tkinter.StringVar()
		self.GPSlongitudeText.set("%f"%(self.longitudeGPS))
		tmp = Tkinter.Label(tmpGroup, textvariable=self.GPSlongitudeText, bg='white', anchor="w", font="Helvetica 12")
		tmp.grid(row=row+3, column=col+2)


		tmp = Tkinter.Label(tmpGroup, text="Satellites", bg='white', anchor="w", font="Helvetica 12")
		tmp.grid(row=row+4, column=col)

		tmp = Tkinter.Label(tmpGroup, text=" - ", bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row+4, column=col+1)

		self.GPSsatellitesText = Tkinter.StringVar()
		self.GPSsatellitesText.set("%d"%(self.satellitesGPS))
		tmp = Tkinter.Label(tmpGroup, textvariable=self.GPSsatellitesText, bg='white', anchor="w", font="Helvetica 12")
		tmp.grid(row=row+4, column=col+2)



		#Buttons
		col = 2
		row = 1


		phoneGroup = Tkinter.LabelFrame(rightGroup, text="Call operations", bg='white', padx=5, pady=5)
		phoneGroup.grid(row=row, column=col)

		tmpGroup = Tkinter.LabelFrame(phoneGroup, bg='white', bd=0, padx=5, pady=5)
		tmpGroup.grid(row=row, column=col)

		ButtonGPS = Tkinter.Button(tmpGroup, text="E-call", command=self.ActionMakeEcall, font = "Helvetica 14")
		ButtonGPS.grid(row=row, column=col, padx=5, pady=10)

		ButtonGPS = Tkinter.Button(tmpGroup, text="Voice call", command=self.ActionMakeVoiceCall, font = "Helvetica 14")
		ButtonGPS.grid(row=row, column=col+1, padx=5, pady=10)

		ButtonGPS = Tkinter.Button(tmpGroup, text="Send SMS", command=self.ActionMakeSMS, font = "Helvetica 14")
		ButtonGPS.grid(row=row, column=col+2, padx=5, pady=10)

		ButtonGPS = Tkinter.Button(tmpGroup, text="Geolocation", command=self.ActionConnectGPS, font = "Helvetica 14")
		ButtonGPS.grid(row=row, column=col+3, padx=5, pady=10)



		actionsGroup = Tkinter.LabelFrame(rightGroup, text="File operations", bg='white', padx=5, pady=5)
		actionsGroup.grid(row=row+1, column=col)

		tmpGroup = Tkinter.LabelFrame(actionsGroup, bg='white', bd=0, padx=5, pady=5)
		tmpGroup.grid(row=row, column=col)

		ButtonGPS = Tkinter.Button(tmpGroup, text="Send Card.bin", command=self.ActionSendFile, font = "Helvetica 14") #state='disabled'
		ButtonGPS.grid(row=row, column=col, padx=5, pady=10)

		ButtonGPS = Tkinter.Button(tmpGroup, text="Get bin file", command=self.ActionGetBinaryFile, font = "Helvetica 14")
		ButtonGPS.grid(row=row, column=col+1, padx=5, pady=10)

		ButtonGPS = Tkinter.Button(tmpGroup, text="Get xml file", command=self.ActionGetConfigFile, font = "Helvetica 14")
		ButtonGPS.grid(row=row, column=col+2, padx=5, pady=10)

		ButtonGPS = Tkinter.Button(tmpGroup, text="Get infos", command=self.ActionGetInfo, font = "Helvetica 14")
		ButtonGPS.grid(row=row, column=col+3, padx=5, pady=10)


		tmpGroup = Tkinter.LabelFrame(actionsGroup, bg='white', bd=0, padx=5, pady=5)
		tmpGroup.grid(row=row+1, column=col)

		tmp = Tkinter.Label(tmpGroup, text=" 0% ", bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row+1, column=col)

		self.myprogressbar = ttk.Progressbar(tmpGroup, length = 200, mode ="determinate") #play with maximum and value
		self.myprogressbar.grid(row=row+1, column=col+1, padx=5, pady=10)

		tmp = Tkinter.Label(tmpGroup, text=" 100% ", bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row+1, column=col+2)

		self.RXTXstatusText = Tkinter.StringVar()
		self.RXTXstatusText.set("Awaiting orders")
		tmp = Tkinter.Label(tmpGroup, textvariable=self.RXTXstatusText, bg='white', anchor="w", font="Helvetica 14")
		tmp.grid(row=row+1, column=col+3)


		consoleGroup = Tkinter.LabelFrame(rightGroup, text="Console", bg='white', padx=5, pady=5)
		consoleGroup.grid(row=row+2, column=col)


		#termf = Tkinter.Frame(consoleGroup, height=340, width=530)
		#termf.grid(row=row, column=col)
		self.consolePrompt = Tkinter.Text(consoleGroup, height=22, width=75)
		self.consolePrompt.grid(row=row, column=col)

		self.consolePrompt.insert(Tkinter.INSERT, "Schiller GSM testbench V%s\n"%(__version__))


		


	def reloadImage(self, myimage, box):
		self.mapImage = ImageTk.PhotoImage(myimage)
		self.image_label = Tkinter.Label(box, image=self.mapImage)
		self.image_label.grid(row=2, column=1)
		self.grid()

	def getDefiMap(self):
		googleMapRequest = "http://maps.google.com/maps/api/staticmap?size=%dx%d&format=png&maptype=roadmap&markers=label:S|color:red|Wissembourg"%(self.sizeMapX, self.sizeMapY)

		# If coordinates available for the device, add its marker
		if self.latitudeGPS != 0 or self.longitudeGPS != 0:
			googleMapRequest += "&markers=label:D|color:blue|%f,%f"%(self.latitudeGPS, self.longitudeGPS)
		else:
			latitudeAnchor = 49.023180
			longitudeAnchor = 7.962005
		
		googleMapRequest += "&sensor=false&"
		
		response = requests.get(googleMapRequest)
		img = Image.open(StringIO(response.content))

		return img

	def EnterPressed(self, event):
		print "Enter!"
		#self.latitudeGPS -= 0.010
		#self.longitude -= 0.010
		#self.reloadImage(self.getDefiMap(), self.trackGroup)

		self.ProgressbarVal += 1

		self.myprogressbar['maximum'] = 100
		self.myprogressbar['value'] = self.ProgressbarVal
		print "Progress = %d / 100"%(self.ProgressbarVal)


	def setModem(self, modem):
		self.modemClass = modem
		self.ActionProvideVersion()


	# Methods used by the modem to update status
	def Update_Connections(self, ecall, voiceCall, dataCall):
		if ecall == True:
			self.ecallText.set("Connected")
			self.ecallStatus['fg']='green' # couleur de fond
		else:
			self.ecallText.set("Disconnected")
			self.ecallStatus['fg']='red' # couleur de fond

		if voiceCall == True:
			self.voicecallText.set("Connected")
			self.voicecallStatus['fg']='green' # couleur de fond
		else:
			self.voicecallText.set("Disconnected")
			self.voicecallStatus['fg']='red' # couleur de fond

		if dataCall == True:
			self.datacallText.set("Connected")
			self.datacallStatus['fg']='green' # couleur de fond
		else:
			self.datacallText.set("Disconnected")
			self.datacallStatus['fg']='red' # couleur de fond

	def UpdateGPScoordinates(self, lati, longi, satellites):
		if lati != 0 and longi != 0:
			self.latitudeGPS = lati - self.movement
			self.longitudeGPS = longi
			self.satellitesGPS = satellites

			self.GPSlatitudeText.set("%f"%(self.latitudeGPS))
			self.GPSlongitudeText.set("%f"%(self.longitudeGPS))
			self.GPSsatellitesText.set("%d"%(self.satellitesGPS))
		#else:
		#	self.latitudeGPS = self.latitudeAnchor - self.movement
		#	self.longitudeGPS = self.longitudeAnchor

		self.movement += 0.01

		self.reloadImage(self.getDefiMap(), self.trackGroup)

	def UpdateGPSstatus(self, status):
		if status == True:
			self.statusGPStext.set("Activated")
			self.trackerStatus['fg'] = 'green'
		else:
			self.statusGPStext.set("Disabled")
			self.trackerStatus['fg'] = 'red'

		#TODO : Add color

	def UpdatePortion(self, val):
		self.myprogressbar['maximum'] = 100
		self.myprogressbar['value'] = val

		print "Progress = %f / 100"%(val)

	def UpdateConsolePrompt(self, text):
		self.consolePrompt.insert(Tkinter.INSERT, text)


	# Methods used by the display to pilot modem
	def ActionProvideVersion(self):
		self.modemClass.ActionDisplayVersion(__version__)

	def ActionConnectGPS(self):
		self.modemClass.ActionActivateGPS()

	def ActionDisconnect(self):
		self.modemClass.ActionShutdown()

	def ActionSendFile(self):
		self.modemClass.ActionPutCardbin()

	def ActionGetBinaryFile(self):
		self.modemClass.ActionGetBinary()

	def ActionGetConfigFile(self):
		self.modemClass.ActionGetConfig()

	def ActionGetInfo(self):
		self.modemClass.ActionGetInfo()


	def ActionMakeEcall(self):
		self.modemClass.ActionMakeEcall()

	def ActionMakeVoiceCall(self):
		self.modemClass.ActionMakeVoiceCall()

	def ActionMakeSMS(self):
		self.modemClass.ActionMakeSMS()