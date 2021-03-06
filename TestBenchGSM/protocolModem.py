#!/usr/bin/env python
"""ModemProto: Class for 128PROT communication with Schiller GSM"""
__author__ ="Julien Beaudaux"
__version__ = "0.2"
__email__ = "julien.beaudaux@schiller.fr"

import sys, os, serial, time, base64
import datetime
from threading import Thread, Timer, Lock
from termcolor import colored, cprint
from crc8 import Crc8
from ConfigParser import SafeConfigParser
from serial.tools.list_ports import comports

import urllib2


# The protocol used is 128PROT
# The frames are in the following form, with 2 characters being one byte (as in Hexa)
#   88   AAAA  BBBB  CC  DD  EEEE  FFFF......  GG  A5
# The frame start (SOF) and frame end (EOF) are always respectively 88 and A5 
# AAAA : The "Length of Data" (LOD) field is the total length of the FFFF field
# BBBB : The "Frame counter" (FCT) field is an incremental value of the frame sent for this session
#  CC  : The "Frame type" (FTY) field refers to the role of the frame in the handshake phase
#        It can be 1 (Identification Frames), 2 (Transfer Mode Frames), 3 (KeepAlive Frames) or 4 (GSM protocol data frames)
#  DD  : The "Header CRC" (HCRC), is the CRC of the fields AAAA, BBBB and CC
# EEEE : The "Data Identifier" (DI) field represents the GSM protocol command/value type. It is used only when CC is 4.
# FFFF : The "Data" field contains the GSM protocol command/value additional data. Its size is variable. It is used only when CC is 4.
#  GG  : The "Data CRC" (DCRC), is the CRC of the fields EEEE and FFFF


class ModemProto():
	def __init__(self):
		self.TXcardbinMode   = False
		self.TXautotestMode  = False
		self.RXdataMode      = False

		self.dataAckResult    = False
		self.continueResult   = False
		self.responseNeeded   = False
		self.httpResponseCode = -1
		self.HTTPattempts      = 0

		self.RXpart           = 0
		self.RXtotlen         = 0
		self.RXstart          = 0

		self.TXdelay          = 0.3

		self.time_start       = 0
		self.frame_counter    = 0
		self.PutFile          = "to_sema/card.bin"
		self.AutotestFile     = "to_sema/autotestHTML.html"

		#State machine states
		self.STATE_WAIT       = 0
		self.STATE_MIF        = 1
		self.STATE_MTMF       = 2
		self.STATE_MKA        = 3
		self.STATE_CONNECTED  = 4

		self.filebin          = None

		self.consoleProofFile = None

		self.crcCalc = Crc8()

		# Get configuration
		config = SafeConfigParser()
		config.read('config.ini')

		self.url_server  = config.get('server', 'url')
		self.login       = config.get('server', 'login')
		self.password    = config.get('server', 'password')
		self.ip_server   = config.get('server', 'ip_address')
		self.https_mode  = config.get('server', 'https_mode')
		self.http_port   = config.get('server', 'http_port')
		self.https_port  = config.get('server', 'https_port')
		self.app_id      = config.get('server', 'app_id')
		self.ver_id      = config.get('server', 'ver_id')
		self.xml_file    = config.get('server', 'xml_file')
		self.bin_file    = config.get('server', 'bin_file')

		self.apn         = config.get('sim','apn')
		self.voice_num   = config.get('sim','voice_num')
		self.ecall_num   = config.get('sim','ecall_num')
		self.sms_text    = config.get('sim','sms_text')

		key = "%s:%s"%(self.login,self.password)
		key = base64.b64encode(key)

		if self.https_mode == "no":
			self.get_bin_file = "GET http://%s:%s/SUS/public/v1/image/%s/%s/%s HTTP/1.1\r\nHost: %s:%s\r\nAccept-Encoding: identity\r\ncontent-type: application/octet-stream; charset=UTF-8\r\nAuthorization: Basic %s \r\n\r\n "%(self.url_server, self.http_port, self.app_id,self.ver_id,self.bin_file, self.url_server, self.http_port, key )
			self.get_xml_file = "GET http://%s:%s/SUS/public/v1/settingset/%s/%s/%s HTTP/1.1\r\nHost: %s:%s\r\nAccept-Encoding: identity\r\ncontent-type: application/xml; charset=UTF-8\r\nAuthorization: Basic %s \r\n\r\n "%(self.url_server, self.http_port, self.app_id,self.ver_id,self.xml_file, self.url_server, self.http_port, key )
			self.get_info     = "GET http://%s:%s/SUS/public/v1/info HTTP/1.1\r\nHost: %s:%s\r\nAccept-Encoding: identity\r\ncontent-type: text/plain; charset=UTF-8\r\nAuthorization: Basic %s\r\n\r\n"%(self.url_server, self.http_port, self.url_server, self.http_port, key )
			self.get_manifest = "GET http://%s:%s/SUS/public/v1/manifest/%s/vid/%s HTTP/1.1\r\nHost: %s:%s\r\nAccept-Encoding: identity\r\ncontent-type: text/plain; charset=UTF-8\r\nAuthorization: Basic %s\r\n\r\n"%(self.url_server, self.http_port, self.app_id, self.ver_id, self.url_server, self.http_port, key)
			
			self.put_keepalive = "PUT http://%s:%s/SemaServer/public/v2/devices/alive HTTP/1.1\r\nHost: %s:%s\r\nAccept-Encoding: identity\r\nContent-type: application/json; charset=UTF-8\r\nContent-Length: 228\r\nAuthorization: Basic %s\r\n\r\n{\"serialNumber\": \"127999999999\", \"applicationId\": \"2.16.756.5.25.4.6.2.1\", \"deviceId\": \"127999999999\", \"model\": \"FRED PA-1\", \"swVersion\": \"01.01B06\", \"hwVersion\": \"301\", \"location\": {\"longitude\": \"7.0\", \"latitude\": \"49.023651\"}}"%(self.url_server, self.http_port, self.url_server, self.http_port, key )
			self.put_card_bin  = "PUT http://%s:%s/SemaConverter/CardBin HTTP/1.1\r\nHost: %s:%s \r\nAccept: */*\r\nContent-Type: application/octet-stream\r\nExpect: 100-continue\r\n"%(self.url_server, self.http_port)
			self.post_autotest = "POST /SemaServer/public/v2/devices/message HTTP/1.1\r\nHost: %s:%s\r\nAccept: */*\r\nAccept-Encoding: identity\r\ncontent-Type: application/json; charset=UTF-8\r\nAuthorization: Basic %s\r\n\r\n{\"level\": \"INFO\", \"serialNumber\": \"127999999999\", \"message\": \"<!DOCTYPE html>\\n<html lang=\\\"en\\\">\\n<head>\\n\\t<meta charset=\\\"UTF-8\\\">\\n\\t<title></title>\\n</head>\\n<body>\\n\\t<h1>Test Result</h1>\\n\\t<p>Device State</p>\\n\\t<ul>\\n\\t\\t<li><a href=\\\"google.com\\\">un</a></li>\\n\\t\\t<li><a href=\\\"google.com\\\">deux</a></li>\\n\\t\\t<li><a href=\\\"google.com\\\">trois</a></li>\\n\\t</ul>\\n</body>\\n</html>\\n\", \"subject\": \"Test\", \"applicationId\": \"2.16.756.5.25.4.6.1.1\", \"shortMessage\": \"Test MND\"}"%(self.url_server, self.http_port, self.url_server, self.http_port, key )
		#	self.post_autotest = "POST http://%s:%s/SemaServer/public/v2/devices/message HTTP/1.1\r\nHost: %s:%s\r\nAccept-Encoding: identity\r\nContent-Length: 481\r\ncontent-type: application/json; charset=UTF-8\r\nAuthorization: Basic %s\r\n\r\n{\"level\": \"INFO\", \"serialNumber\": \"127999999999\", \"message\": \"<!DOCTYPE html>\\n<html lang=\\\"en\\\">\\n<head>\\n\\t<meta charset=\\\"UTF-8\\\">\\n\\t<title></title>\\n</head>\\n<body>\\n\\t<h1>Test Result</h1>\\n\\t<p>Device State</p>\\n\\t<ul>\\n\\t\\t<li><a href=\\\"google.com\\\">un</a></li>\\n\\t\\t<li><a href=\\\"google.com\\\">deux</a></li>\\n\\t\\t<li><a href=\\\"google.com\\\">trois</a></li>\\n\\t</ul>\\n</body>\\n</html>\\n\", \"subject\": \"Test\", \"applicationId\": \"2.16.756.5.25.4.6.2.1\", \"shortMessage\": \"Test MND\"}"%(self.url_server, self.http_port, self.url_server, self.http_port, key )

		else:
			self.get_bin_file = "GET https://%s:%s/SUS/public/v1/image/%s/%s/%s HTTP/1.1\r\nHost: %s:%s\r\nAccept-Encoding: identity\r\ncontent-type: application/octet-stream; charset=UTF-8\r\nAuthorization: Basic %s \r\n\r\n"%(self.url_server, self.https_port, self.app_id,self.ver_id,self.bin_file, self.url_server, self.https_port, key )
			self.get_xml_file = "GET https://%s:%s/SUS/public/v1/settingset/%s/%s/%s HTTP/1.1\r\nHost: %s:%s\r\nAccept-Encoding: identity\r\ncontent-type: application/xml; charset=UTF-8\r\nAuthorization: Basic %s \r\n\r\n"%(self.url_server, self.https_port, self.app_id,self.ver_id, self.xml_file, self.url_server, self.https_port, key )
			self.get_info     = "GET https://%s:%s/SUS/public/v1/info HTTP/1.1\r\nHost: %s:%s\r\nAccept-Encoding: identity\r\ncontent-type: text/plain; charset=UTF-8\r\nAuthorization: Basic %s\r\n\r\n"%(self.url_server, self.https_port, self.url_server, self.https_port, key )
			self.get_manifest = "GET https://%s:%s/SUS/public/v1/manifest/%s/vid/%s HTTP/1.1\r\nHost: %s:%s\r\nAccept-Encoding: identity\r\ncontent-type: text/plain; charset=UTF-8\r\nAuthorization: Basic %s\r\n\r\n"%(self.url_server, self.https_port, self.app_id, self.ver_id, self.url_server, self.https_port, key)
			
			self.put_keepalive = "PUT https://%s:%s/SemaServer/public/v2/devices/alive HTTP/1.1\r\nHost: %s:%s\r\nAccept-Encoding: identity\r\nContent-type: application/json; charset=UTF-8\r\nContent-Length: 228\r\nAuthorization: Basic %s\r\n\r\n{\"serialNumber\": \"127999999999\", \"applicationId\": \"2.16.756.5.25.4.6.2.1\", \"deviceId\": \"127999999999\", \"model\": \"FRED PA-1\", \"swVersion\": \"01.01B06\", \"hwVersion\": \"301\", \"location\": {\"longitude\": \"7.0\", \"latitude\": \"49.023651\"}}"%(self.url_server, self.https_port, self.url_server, self.https_port, key)
			self.put_card_bin  = "PUT https://%s:%s/SemaConverter/CardBin HTTP/1.1\r\nHost: %s:%s \r\nAccept: */*\r\nContent-Type: application/octet-stream\r\nExpect: 100-continue\r\n"%(self.url_server, self.https_port, self.url_server, self.https_port)
			self.post_autotest = "POST /SemaServer/public/v2/devices/message HTTP/1.1\r\nHost: %s:%s\r\nAccept: */*\r\nAccept-Encoding: identity\r\nContent-Type: application/json; charset=UTF-8\r\nAuthorization: Basic %s\r\nExpect: 100-continue\r\n"%(self.url_server, self.https_port, key )# Content-Length: 494\r\nAuthorization: Basic %s\r\n\r\n{\"level\": \"INFO\", \"serialNumber\": \"127000000000\", \"message\": \"<!DOCTYPE html>\\n<html lang=\\\"en\\\">\\n<head>\\n\\t<meta charset=\\\"UTF-8\\\">\\n\\t<title></title>\\n</head>\\n<body>\\n\\t<h1>Test Result</h1>\\n\\t<p>Device State</p>\\n\\t<ul>\\n\\t\\t<li><a href=\\\"google.com\\\">un</a></li>\\n\\t\\t<li><a href=\\\"google.com\\\">deux</a></li>\\n\\t\\t<li><a href=\\\"google.com\\\">trois</a></li>\\n\\t</ul>\\n</body>\\n</html>\\n\", \"subject\": \"Test\", \"applicationId\": \"2.16.756.5.25.4.6.1.1\", \"shortMessage\": \"Test MND\"}"%(self.url_server, self.https_port, self.url_server, self.https_port, key )
		#	self.post_autotest = "POST https://%s:%s/SemaServer/public/v2/devices/message HTTP/1.1\r\nHost: %s:%s\r\nAccept-Encoding: identity\r\nContent-Length: 481\r\ncontent-type: application/json; charset=UTF-8\r\nAuthorization: Basic %s\r\n\r\n{\"level\": \"INFO\", \"serialNumber\": \"127999999999\", \"message\": \"<!DOCTYPE html>\\n<html lang=\\\"en\\\">\\n<head>\\n\\t<meta charset=\\\"UTF-8\\\">\\n\\t<title></title>\\n</head>\\n<body>\\n\\t<h1>Test Result</h1>\\n\\t<p>Device State</p>\\n\\t<ul>\\n\\t\\t<li><a href=\\\"google.com\\\">un</a></li>\\n\\t\\t<li><a href=\\\"google.com\\\">deux</a></li>\\n\\t\\t<li><a href=\\\"google.com\\\">trois</a></li>\\n\\t</ul>\\n</body>\\n</html>\\n\", \"subject\": \"Test\", \"applicationId\": \"2.16.756.5.25.4.6.2.1\", \"shortMessage\": \"Test MND\"}"%(self.url_server, self.https_port, self.url_server, self.https_port, key )


	def read_frame(self):
		eof = 'A5'.decode('hex')
		sof = '88'.decode('hex')
		line = bytearray()
		read_error = False
		i=0
		k=0
		len0=0
		while True:
			try:
				c = self.serport.read(1)
				read_error = False
			except serial.serialutil.SerialException:
				read_error = True
				c = ''
			if c:
				line+=c
				if (i==0):
					if(c==sof):
						i+=1
				else:
					if(i==1):
						c1=c.encode('hex')
						len0=int(c1,16)
						i+=1
						#print len0
					elif(i==2):
						c1=c.encode('hex')
						len0=len0*256+int(c1,16)
						i+=1
					elif(k<len0+6):
						k+=1
						if(k==len0+6):
							break
			elif read_error == False:
				break
		return bytes(line)


	def forgeNewFrame(self, FTY, DI, DATA, retransmit=False):
		if False == retransmit:
			self.frame_counter += 1
		
		forgedFrame = "88"

		dataZone = DI + DATA

		myLod = hex((len(dataZone) / 2))[2:]
		myLod = '{:0>4}'.format(myLod) 
		forgedFrame += myLod

		frameCnt = hex(self.frame_counter)[2:]
		frameCnt = '{:0>4}'.format(frameCnt)
		forgedFrame += frameCnt

		forgedFrame += FTY

		myHcrc = hex(self.crcCalc.digest(forgedFrame))[2:]
		myHcrc = '{:0>2}'.format(myHcrc)
		self.crcCalc.resetCRC()
		forgedFrame += myHcrc

		myDcrc = hex(self.crcCalc.digest(dataZone))[2:]
		myDcrc = '{:0>2}'.format(myDcrc)
		self.crcCalc.resetCRC()

		forgedFrame += dataZone
		forgedFrame += myDcrc

		forgedFrame += "A5"

		if DI == '04':
			self.responseNeeded = True

		return forgedFrame

	def forgeBinaryFrame(self, DATA, retransmit=False):
		if False == retransmit:
			self.frame_counter += 1

		forgedFrame = "88"

		myDATAlen = hex((len(DATA)))[2:]
		myDATAlen = '{:0>4}'.format(myDATAlen) 

		dataZone = "13AA" + myDATAlen + DATA.encode('hex')

		myLod = hex((len(dataZone) / 2))[2:]
		myLod = '{:0>4}'.format(myLod) 
		forgedFrame += myLod

		frameCnt = hex(self.frame_counter)[2:]
		frameCnt = '{:0>4}'.format(frameCnt)
		forgedFrame += frameCnt

		forgedFrame += "04"

		myHcrc = hex(self.crcCalc.digest(forgedFrame))[2:]
		myHcrc = '{:0>2}'.format(myHcrc)
		self.crcCalc.resetCRC()
		forgedFrame += myHcrc

		myDcrc = hex(self.crcCalc.digest(dataZone))[2:]
		myDcrc = '{:0>2}'.format(myDcrc)
		self.crcCalc.resetCRC()

		forgedFrame += dataZone
		forgedFrame += myDcrc

		forgedFrame += "A5"

		return forgedFrame


	# Master Identification Frame
	def send_cmd_mif(self):
		#mif = "88 00 00 00 00 01 CC 00 A5"
		#mif = mif.replace(" ", "")
		mif = self.forgeNewFrame("01", "", "")
		mif = mif.decode('hex')

		self.printAsProof("-----> Master Identification Frame", "blue")
		self.printAsProof(mif.encode('hex'), "blue")

		self.serport.write(mif)

	# Master Transfer Mode Frame
	def send_cmd_mtmf(self):
		#mtmf = "88 00 04 00 01 02 CC 02 01 00 03 CC A5"
		#mtmf = mtmf.replace(" ", "")
		mtmf = self.forgeNewFrame("02", "0201", "0003")
		mtmf = mtmf.decode('hex')

		self.printAsProof("-----> Master Transfer Mode Frame", "blue")
		self.printAsProof(mtmf.encode('hex'), "blue")

		self.serport.write(mtmf)

	# Master KeepAlive Frame
	def send_cmd_mkaf(self):
		#mkaf = "88 00 00 00 02 03 CC 00 A5"
		#mkaf = mkaf.replace(" ", "")
		mkaf = self.forgeNewFrame("03", "", "")
		mkaf = mkaf.decode('hex')

		self.printAsProof("-----> Master Keep Alive Frame", "blue")
		self.printAsProof(mkaf.encode('hex'), "blue")

		self.serport.write(mkaf)

	# 1300 ECALL ON/OFF
	def send_cmd_ecall(self,state):
		if state ==  1:
			ecall_on = self.forgeNewFrame("04", "1300", "01")
			ecall_on = ecall_on.decode('hex')

			self.printAsProof("-----> ECall ON", "blue")
			self.printAsProof(ecall_on.encode('hex'), "blue")
			
			self.serport.write(ecall_on)


		elif state == 0:
			ecall_off = self.forgeNewFrame("04", "1300", "00")
			ecall_off = ecall_off.decode('hex')

			self.printAsProof("-----> ECall OFF", "blue")
			self.printAsProof(ecall_off.encode('hex'), "blue")

			self.serport.write(ecall_off)

	# 1301 VOICE CALL ON/OFF
	def send_cmd_voicecall(self,state):
		if state ==  1:
			voiceCall_data = "01"

			i=0
			while i <= len(self.voice_num)-1:
				voiceCall_data += self.voice_num[i].encode('hex')
				i += 1
			
			i=0
			while i < 25 - len(self.voice_num):
				voiceCall_data += "00"
				i+=1

			voice_call_on = self.forgeNewFrame("04", "1301", voiceCall_data)
			voice_call_on = voice_call_on.decode('hex')

			self.printAsProof("-----> Voice Call ON", "blue")
			self.printAsProof(voice_call_on.encode('hex'), "blue")

			self.serport.write(voice_call_on)
		elif state == 0:
			voiceCall_data = "00"

			i=0
			while i <= len(self.voice_num)-1:
				voiceCall_data += self.voice_num[i].encode('hex')
				i += 1
			
			i=0
			while i < 25 - len(self.voice_num):
				voiceCall_data += "00"
				i+=1
			
			voice_call_off = self.forgeNewFrame("04", "1301", voiceCall_data)
			voice_call_off = voice_call_off.decode('hex')

			self.printAsProof("-----> Voice Call OFF", "blue")
			self.printAsProof(voice_call_off.encode('hex'), "blue")

			self.serport.write(voice_call_off)

	# 1302 DATA CALL ON/OFF
	def send_cmd_data_call(self,state):
		if state ==  1:
			data_call_on = self.forgeNewFrame("04", "1302", "01")
			data_call_on = data_call_on.decode('hex')

			self.printAsProof("-----> Data Call ON", "blue")
			self.printAsProof(data_call_on.encode('hex'), "blue")

			self.serport.write(data_call_on)
		elif state == 0:
			data_call_off = self.forgeNewFrame("04", "1302", "00")
			data_call_off =data_call_off.decode('hex')

			self.printAsProof("-----> Data Call OFF", "blue")
			self.printAsProof(data_call_off.encode('hex'), "blue")

			self.serport.write(data_call_off)

	# 1303 GET GPS Position
	# Data : XX YY ZZ - XX = ON/OFF (01/00) - YY ZZ = Transfer interval
	def send_cmd_gps(self,state):
		if state ==  1:
			gps_on = self.forgeNewFrame("04", "1303", "010010")
			gps_on = gps_on.decode('hex')

			self.printAsProof("-----> GPS Position ON", "blue")
			self.printAsProof(gps_on.encode('hex'), "blue")

			self.serport.write(gps_on)

		elif state == 0:
			gps_off = self.forgeNewFrame("04", "1303", "000060")
			gps_off = gps_off.decode('hex')

			self.printAsProof("-----> GPS Position OFF", "blue")
			self.printAsProof(gps_off.encode('hex'), "blue")

			self.serport.write(gps_off)


	# 1305 SEND SMS
	def send_cmd_sms(self):
		smsData = ""
		i=0
		while i <= len(self.voice_num)-1:
			smsData += self.voice_num[i].encode('hex')
			i += 1

		i=0
		while i < 25 - len(self.voice_num):
			smsData += "00"
			i+=1

		i=0
		while i <= len(self.sms_text)-1:
			smsData += self.sms_text[i].encode('hex')
			i += 1

		i=0
		while i < 140 - len(self.sms_text):
			smsData += "00"
			i+=1
		
		sms = self.forgeNewFrame("04", "1305", smsData)
		sms = sms.decode('hex')

		self.printAsProof("-----> Send SMS", "blue")
		self.printAsProof(sms.encode('hex'), "blue")

		self.serport.write(sms)


	# 1306 SET CONFIG
	def send_cmd_set_config(self):
		i=0
		while i <= len(self.ip_server)-1:
			configData += self.ip_server[i].encode('hex')
			i += 1

		i=0
		while i < 20 - len(self.ip_server):
			configData += '\0'.encode('hex')
			i+=1

		#apn
		i=0
		while i <= len(self.apn)-1:
			configData+= self.apn[i].encode('hex')
			i += 1

		i=0
		while i < 32 - len(self.apn):
			configData += '\0'.encode('hex')
			i+=1

		#url
		i=0
		while i <= len(self.url_server)-1:
			configData += self.url_server[i].encode('hex')
			i += 1

		i=0
		while i < 64 - len(self.url_server):
			configData += '\0'.encode('hex')
			i+=1

		#port
		i=0
		while i <= len(self.port_server)-1:
			configData += self.port_server[i].encode('hex')
			i += 1

		i=0
		while i < 4 - len(self.port_server):
			configData += '\0'.encode('hex')
			i+=1

		#acc
		i=0
		while i <= len(self.login)-1:
			configData += self.login[i].encode('hex')
			i += 1

		i=0
		while i < 32 - len(self.login):
			configData += '\0'.encode('hex')
			i+=1

		#pwd
		i=0
		while i <= len(self.password)-1:
			configData += self.password[i].encode('hex')
			i += 1

		i=0
		while i < 32 - len(self.password):
			configData += '\0'.encode('hex')
			i+=1
		
		#voice number
		i=0
		while i <= len(self.voice_num)-1:
			configData += self.voice_num[i].encode('hex')
			i += 1

		i=0
		while i < 25 - len(self.voice_num):
			configData += "00"
			i+=1

		#ecall number
		i=0
		while i <= len(self.ecall_num)-1:
			configData+= self.ecall_num[i].encode('hex')
			i += 1

		i=0
		while i < 25 - len(self.ecall_num):
			configData += "00"
			i+=1

		config = self.forgeNewFrame("04", "1306", configData)
		config = config.decode('hex')

		self.printAsProof("-----> Set Config [1306]", "blue")
		self.printAsProof(config.encode('hex'), "blue")

		self.serport.write(config)

	# 1307 wait_dataWait Data
	def send_cmd_wait_data(self):
		wait_data = self.forgeNewFrame("04", "1307", "00FF09")
		wait_data = wait_data.decode('hex')

		self.printAsProof("-----> GET_DATA_FRAME [1307]", "blue")
		self.printAsProof(wait_data.encode('hex'), "blue")

		self.serport.write(wait_data)

	#1309
	def send_cmd_get_config(self):
		get_config = self.forgeNewFrame("04", "1309", "")
		get_config = get_config.decode('hex')

		self.printAsProof("-----> Get init settings [1309]", "blue")
		self.printAsProof(get_config.encode('hex'), "blue")

		self.serport.write(get_config)

	 # 1356 GET MODEM GET MODEM STATUS
	def send_cmd_get_modem_status(self):
		get_modem_status = self.forgeNewFrame("04", "1356", "")
		get_modem_status = get_modem_status.decode('hex')

		self.printAsProof("-----> Get Modem Status [1356]", "blue")
		self.printAsProof(get_modem_status.encode('hex'), "blue")

		self.serport.write(get_modem_status)

	# 1357 GET Ecall Data
	def send_cmd_get_ecall_data(self):
		get_ecall_data = self.forgeNewFrame("04", "1357", "")
		get_ecall_data = get_ecall_data.decode('hex')

		self.printAsProof("-----> Get Ecall Data [1357]", "blue")
		self.printAsProof(get_ecall_data.encode('hex'), "blue")

		self.serport.write(get_ecall_data)


	# 13AA SEND Data
	def send_cmd_get_xml_file(self, manifest=True):
		if manifest == False:
			data = self.get_xml_file
			filName = self.xml_file
		else:
			data = self.get_manifest
			filName = "manifest"

		self.get_xml_file_proof(data, filName)

		self.RXdataMode = True
		self.RXpart = 0
		self.RXstart = int(time.time())
		self.filebin = open("proof/%d_Device_%s.xml"%(int(time.time()), filName), "wb")

		datalen = len(data)
		len_hex = hex(datalen)[2:]
		len_hex = '{:0>4}'.format(len_hex)

		requestData = len_hex

		i=0
		while i <= len(data)-1:
			requestData += data[i].encode('hex')
			i += 1

		request = self.forgeNewFrame("04", "13AA", requestData)
		request = request.decode('hex')

		self.printAsProof("-----> Send Resquest [13AA] : %s"%(data), "blue")
		self.printAsProof(request.encode('hex'), "blue")

		self.serport.write(request)
		self.waitServerResponse()


	def get_xml_file_proof(self, link, fileName="XML"):
		url = link.split(" ")[1]

		self.printAsProof("-----> GET XML file from desktop for comparison : URL %s -- File proof/%d_Desktop_%s.xml"%(url, self.time_start, fileName), "magenta")

		proof = open("proof/%d_Desktop_%s.xml"%(self.time_start, fileName), "wb")
		proof.write(urllib2.urlopen(url).read())
		proof.close()
		self.printAsProof("<----- GET XML file from desktop --- Received proof --- file proof/%d_Desktop_%s.xml"%(self.time_start, fileName), "magenta")



	# Directly downloads from the server without using GSM, for later comparison
	def get_bin_file_proof(self):
		url = self.get_bin_file.split(" ")[1]
		
		self.printAsProof("-----> GET BIN file from desktop for comparison : URL %s -- File proof/%d_Desktop_%s"%(url, self.time_start, self.bin_file), "magenta")

		proof = open("proof/%d_Desktop_%s"%(self.time_start, self.bin_file), "wb")
		proof.write(urllib2.urlopen(url).read())
		proof.close()
		self.printAsProof("<----- GET BIN file from desktop --- Received proof --- file proof/%d_Desktop_%s"%(self.time_start, self.bin_file), "magenta")

	# 13AA SEND Data
	def send_cmd_get_bin_file(self):
		self.RXdataMode = True
		self.RXpart = 0
		self.RXstart = int(time.time())

		self.filebin = open("proof/%d_Device_%s"%(self.time_start, self.bin_file), "wb")
		self.printAsProof("GET binary file proof directly from server (%s)"%(self.filebin), "magenta")

		datalen = len(self.get_bin_file)
		len_hex = hex(datalen)[2:]
		len_hex = '{:0>4}'.format(len_hex)
		
		requestData = len_hex
		i=0
		while i <= len(self.get_bin_file)-1:
			requestData += self.get_bin_file[i].encode('hex')
			i += 1
		
		request = self.forgeNewFrame("04", "13AA", requestData)
		request = request.decode('hex')

		self.printAsProof("-----> Send Resquest GET : %s"%(self.get_bin_file), "blue")
		self.printAsProof(request.encode('hex'), "blue")

		self.serport.write(request)

	# 13AA SEND Data
	def send_cmd_get_info(self):
		# First get a proof directly from desktop
		url = self.get_info.split(" ")[1]
		
		self.printAsProof("-----> GET INFO from desktop for comparison : URL %s"%(url), "magenta")
		self.printAsProof("<----- GET INFO from desktop --- Received proof --- %s"%(urllib2.urlopen(url).read()), "magenta")

		datalen = len(self.get_info)
		len_hex = hex(datalen)[2:]
		len_hex = '{:0>4}'.format(len_hex)
		
		requestData = len_hex
		i=0
		while i <= len(self.get_info)-1:
			requestData += self.get_info[i].encode('hex')
			i += 1
		
		request = self.forgeNewFrame("04", "13AA", requestData)
		request = request.decode('hex')

		self.printAsProof("-----> Send GET INFO : %s"%(self.get_info), "blue")
		self.printAsProof(request.encode('hex'), "blue")

		self.serport.write(request)
		self.waitServerResponse()

	# 13AA SEND Data
	def send_cmd_post_autotest(self):
		#self.filebin = open("to_sema/autotestHTML.html", 'r')

		contentLen = os.stat("to_sema/autotestHTML.html").st_size

		contentHTTP = self.post_autotest
		contentHTTP += "Content-Length: %d\r\n\r\n"%(contentLen)

		datalen = len(contentHTTP)
		len_hex = hex(datalen)[2:]
		len_hex = '{:0>4}'.format(len_hex)

		requestData = len_hex
		i=0
		while i < len(contentHTTP):
			requestData += contentHTTP[i].encode('hex')
			i += 1

		request = self.forgeNewFrame("04", "13AA", requestData)
		request = request.decode('hex')

		self.printAsProof("-----> Send Resquest POST : %s"%(contentHTTP), "blue")
		self.printAsProof(request.encode('hex'), "blue")

		self.serport.write(request)
		self.waitServerResponse()

	def send_cmd_put_keepalive(self):
		datalen = len(self.put_keepalive)
		len_hex = hex(datalen)[2:]
		len_hex = '{:0>4}'.format(len_hex)

		requestData = len_hex
		i=0
		while i <= len(self.put_keepalive)-1:
			requestData += self.put_keepalive[i].encode('hex')
			i += 1

		request = self.forgeNewFrame("04", "13AA", requestData)
		request = request.decode('hex')

		self.printAsProof("-----> Send Resquest PUT : %s"%(self.put_keepalive), "blue")
		self.printAsProof(request.encode('hex'), "blue")

		self.serport.write(request)
		self.waitServerResponse()


	def send_cmd_put_card_bin(self):
		data_frame_header = "88 00 0B 00 03 04 CC 13 AA"
		self.put_card_bin += "Content-Length: "
		self.put_card_bin += "%d"%(os.stat(self.PutFile).st_size)
		self.put_card_bin += "\r\n\r\n"
		request = ""
		datalen = len(self.put_card_bin)
		len_hex = hex(datalen)[2:]
		len_hex = '{:0>4}'.format(len_hex)
		request += data_frame_header
		request += len_hex
		i=0
		while i <= len(self.put_card_bin)-1:
			request += self.put_card_bin[i].encode('hex')
			i += 1
		request += "CC A5"
		request = request.replace(" ", "")
		request = request.decode('hex')

		self.printAsProof("-----> Send Resquest PUT : %s"%(self.put_card_bin), "blue")
		self.printAsProof(request.encode('hex'), "blue")

		self.serport.write(request)


	def manage_command(self):
		print "wait command"
		while True:
			inp = raw_input()
			inp = inp + unichr(13)
			ticks = time.time()
			print("TX--------------------> :  %f" %ticks)
			if "1300 0" in inp:
				self.send_cmd_ecall(0)
			elif "1300 1" in inp:
				self.send_cmd_ecall(1)
			elif "1301 0" in inp:
				self.send_cmd_voicecall(0)
			elif "1301 1" in inp:
				self.send_cmd_voicecall(1)
			elif "1302 0" in inp:
				self.send_cmd_data_call(0)
			elif "1302 1" in inp:
				self.send_cmd_data_call(1)
			elif "1303 0" in inp:
				self.send_cmd_gps(0)
			elif "1303 1" in inp:
				self.send_cmd_gps(1)
			elif "1305" in inp:
				self.send_cmd_sms()
			elif "1306" in inp:
				self.send_cmd_set_config()
			elif "1307" in inp:
				self.send_cmd_wait_data()
			elif "1309" in inp:
				self.send_cmd_get_config()
			elif "1356" in inp:
				self.send_cmd_get_modem_status()
			elif "1357" in inp:
				self.send_cmd_get_ecall_data()
			elif "13aa get config" in inp or "13AA get config" in inp:
				self.send_cmd_get_xml_file()
			elif "13aa get binary" in inp or "13AA get binary" in inp:
				self.send_cmd_get_bin_file()
			elif "13aa get info" in inp or "13AA get info" in inp:
				self.send_cmd_get_info()
			elif "13aa post" in inp:
				self.PutRequest_SendAutotest()
				#self.send_cmd_post_autotest()*$
			elif "13aa put" in inp:
				self.PutRequest_SendFiles()
			else :
				self.serport.write(inp)
				
				self.printAsProof("Bad command or args: %s"%(inp), "red")
				self.displayClass.UpdateConsolePrompt("Bad command or args: %s\n"%(inp))

	def manage_orders(self):
		self.orderToPerform = ""
		while True:
			if "TXCARDBIN" in self.orderToPerform:
				self.PutRequest_SendFiles()
				self.orderToPerform = ""

			if "TXTEST" in self.orderToPerform:
				self.PutRequest_SendAutotest()
				#self.send_cmd_post_autotest()
				self.orderToPerform = ""

			if "TXKALIVE" in self.orderToPerform:
				self.send_cmd_put_keepalive()
				self.orderToPerform = ""

	def PutRequest_SendAutotest(self):
		self.TXautotestMode = True

		self.send_cmd_post_autotest()
		self.continueResult = False

		i=0
		while(self.continueResult == False):
			time.sleep(1)
			i+=1
			if(i > 10):
				i=0
				self.send_cmd_post_autotest()

		myfile = open(self.AutotestFile, 'r')
		content = myfile.read(62)

		while len(content) > 0:
			self.dataAckResult = False

			request = self.forgeBinaryFrame(content)
			request = request.decode('hex')

			self.printAsProof("-----> Send Resquest POST : %s"%(content), "blue")
			self.printAsProof(request.encode('hex'), "blue")

			self.serport.write(request)

			i=0
			while self.dataAckResult == False:
				time.sleep(self.TXdelay)
				i+=1
				if(i > 5):
					i=0
					fails+=1

					self.printAsProof("Send Resquest POST FAIL!!! (%d)"%(fails), "red")
					
					self.serport.write(request)
					#self.dataAckResult = True

			content = myfile.read(1024)


		request = self.forgeBinaryFrame("")
		request = request.decode('hex')

		while self.dataAckResult == False:
			time.sleep(self.TXdelay)
			i+=1
			if(i > 5):
				i=0
				fails+=1
				
				self.printAsProof("Send Resquest POST FAIL!!! (%d)"%(fails), "red")
				
				self.serport.write(request)


		self.printAsProof("-----> Send Resquest POST : %s"%(content), "blue")
		self.printAsProof(request.encode('hex'), "blue")

		self.serport.write(request)


		self.printAsProof("File send ended", "yellow")

		time.sleep(3)
		self.send_cmd_wait_data()

		self.TXautotestMode = False




	def PutRequest_SendFiles(self):
		start = int(time.time()) # Considered as the reference time for beginning tests

		self.TXcardbinMode = True

		self.send_cmd_put_card_bin()

		i=0
		while(self.continueResult == False):
			time.sleep(0.5)
			i+=1
			if(i > 10):
				i=0
				self.send_cmd_put_card_bin()

		self.dataAckResult = False

		myfile = open(self.PutFile, 'r')

		comm = ""
		content = myfile.read(1024)
		
		part = 0
		fails = 0



		while len(content) > 0:
			comm = self.forgeBinaryFrame(content)
			comm = request.decode('hex')

			self.printAsProof("-----> PUT File part : %s"%(content), "blue")
			self.printAsProof(comm.encode('hex'), "blue")

			self.displayClass.UpdatePortion((part*100)/((os.stat(self.PutFile).st_size) / 1024))

			self.serport.write(comm)

			content = ""
			content = myfile.read(1024)

			part+=1
			i=0

			while self.dataAckResult == False:
				time.sleep(self.TXdelay)
				i+=1
				if(i > 5):
					i=0
					fails+=1

					self.printAsProof("PUT File part FAIL!!! (%d)"%(fails), "magenta")
					
					self.serport.write(comm)
					#self.dataAckResult = True

			self.dataAckResult = False

		self.printAsProof("File send ended after %d seconds"%(int(time.time()) - start), 'yellow')

		time.sleep(3)
		self.send_cmd_wait_data()

		self.TXcardbinMode = False


	# Method called when a server response is needed 
	def waitServerResponse(self):
		#self.send_cmd_wait_data()
		#timeout = time.time()

		#print "Wait Server Response .... "

		#while 0 < self.httpResponseCode and timeout + 30 > time.time():
		#	pass

		self.responseNeeded = True
		#return


	def manage_response(self, myframe, mystate):
		ticks = time.time()
		#Slave Frame
		if(myframe[0] == '88'.decode('hex')):
			if mystate == self.STATE_MIF:
				if myframe.encode('hex')[10] == '8' and myframe.encode('hex')[11] == '1':
					self.printAsProof("<----- Slave Identification Frame [1381]", "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")
					
					self.send_cmd_mtmf()
					return self.STATE_MTMF

			if mystate == self.STATE_MTMF:
				if myframe.encode('hex')[10] == '8' and myframe.encode('hex')[11] == '2':
					self.printAsProof("<----- Slave Transfer Mode Ack Frame [1382]", "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")

					self.send_cmd_mkaf()
					return self.STATE_MKA

			if mystate == self.STATE_MKA:
				if myframe.encode('hex')[10] == '8' and myframe.encode('hex')[11] == '3':
					# Attempt to initiate data call as soon as turned ON
					self.send_cmd_data_call(1)
					return self.STATE_CONNECTED

			if mystate == self.STATE_CONNECTED:
				if myframe.encode('hex')[16] == '5' and myframe.encode('hex')[17] == '5':
					sat = int(myframe[9].encode('hex'))
					
					a = myframe[19].encode('hex')+myframe[18].encode('hex')+myframe[17].encode('hex')+myframe[16].encode('hex')
					lat = int(a,16)/100000.
					
					a = myframe[23].encode('hex')+myframe[22].encode('hex')+myframe[21].encode('hex')+myframe[20].encode('hex')
					lon = int(a,16)/100000.

					self.printAsProof("<----- GSMVAL_GPS_POSITION  [1355]", "yellow")
					self.printAsProof("Latitude %f ; Longitude %f ; Satellites %d"%(lat, lon, sat), "yellow")
					self.printAsProof("Date %s/%s/%s %s:%s:%s"%(myframe[12].encode('hex'), myframe[11].encode('hex'), myframe[10].encode('hex'), myframe[13].encode('hex'), myframe[14].encode('hex'), myframe[15].encode('hex')), "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")

					self.displayClass.UpdateGPScoordinates(lat, lon, sat)
					self.displayClass.UpdateConsolePrompt("[%d] GPS coord. : %f / %f ; %s sat. ; %s/%s/%s %s:%s:%s \n"%(time.time() - self.time_start, lat, lon, sat, myframe[12].encode('hex'), myframe[11].encode('hex'), myframe[10].encode('hex'), myframe[13].encode('hex'), myframe[14].encode('hex'), myframe[15].encode('hex')))

				elif myframe.encode('hex')[16] == '0' and myframe.encode('hex')[17] == '0':
					self.printAsProof("<----- GSMCMD_ONOFF_E_CALL  [1300]", "yellow")
					self.printAsProof("OFF (0) / ON (1) :  %s"%(myframe[9].encode('hex')), "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")

				elif myframe.encode('hex')[16] == '0' and myframe.encode('hex')[17] == '1':
					self.printAsProof("<----- GSMCMD_ONOFF_VOICE_CALL  [1301]", "yellow")
					self.printAsProof("OFF (0) / ON (1) :  %s"%(myframe[9].encode('hex')), "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")

				elif myframe.encode('hex')[16] == '0' and myframe.encode('hex')[17] == '2':
					self.printAsProof("<----- GSMCMD_ONOFF_DATA_CALL [1302]", "yellow")
					self.printAsProof("OFF (0) / ON (1) :  %s"%(myframe[9].encode('hex')), "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")

				elif myframe.encode('hex')[16] == '0' and myframe.encode('hex')[17] == '3':
					self.printAsProof("<----- GSMCMD_GET_ONOFF_GPS [1303]", "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")

					self.displayClass.UpdateGPSstatus(True)

				elif myframe.encode('hex')[16] == '5' and myframe.encode('hex')[17] == '6':
					self.printAsProof("<----- GSMCMD_GET_MODEM_STATUS [1356]", "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")

					if(myframe[9].encode('hex') == '00'):
						self.printAsProof("E-call in progress    :  %s"%(myframe[9].encode('hex')), 'red')
					else:
						self.printAsProof("E-call in progress    :  %s"%(myframe[9].encode('hex')), 'green')

					if(myframe[11].encode('hex') == '00'):
						self.printAsProof("Voice call in progress:  %s"%(myframe[11].encode('hex')), 'red')
					else:
						self.printAsProof("Voice call in progress:  %s"%(myframe[11].encode('hex')), 'green')

					if(myframe[13].encode('hex') == '00'):
						self.printAsProof("Data call in progress :  %s"%(myframe[13].encode('hex')), 'red')
					else:
						self.printAsProof("Data call in progress :  %s"%(myframe[13].encode('hex')), 'green')

					self.displayClass.Update_Connections(myframe[9].encode('hex') == '01', myframe[11].encode('hex') == '01', myframe[13].encode('hex') == '01')
					self.displayClass.UpdateConsolePrompt("[%d] E-call %s - Voice call %s - Data call %s \n"%(time.time() - self.time_start, myframe[9].encode('hex'), myframe[11].encode('hex'), myframe[13].encode('hex')))

					print("E-call com duration   :  %s"%(myframe[10].encode('hex')))
					print("Voice call duration   :  %s"%(myframe[12].encode('hex')))
					print("Amount of transf data :  %s"%(myframe[14].encode('hex')))
					print("Network strenght      :  %s"%(myframe[16].encode('hex')))
					print("Network provider      :  %s"%(myframe[17:17+32]))

				elif myframe.encode('hex')[16] == '0' and myframe.encode('hex')[17] == '9':###1309 cfg query
					print("RX--------------------------->:  %f" %ticks)
					print ("Unit CFG------>")
					print("IP       :  %s" %(myframe[9:9+20]))
					print("APN      :  %s" %(myframe[29:29+32]))
					print("URL      :  %s" %(myframe[61:61+64]))
					print("PORT     :  %s" %(myframe[125:125+4]))
					print("USER     :  %s" %(myframe[129:129+32]))
					print("PASS     :  %s" %(myframe[161:161+32]))
					print("VOICE    :  %s" %(myframe[193:193+25]))
					print("ECALL    :  %s" %(myframe[218:218+25]))

				elif myframe.encode('hex')[16] == '0' and myframe.encode('hex')[17] == '5':
					self.printAsProof("<----- GSMCMD_SEND_SMS [1305]", "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")

				elif myframe.encode('hex')[16] == '0' and myframe.encode('hex')[17] == '6':
					self.printAsProof("<----- GSMCMD_SET_CONF_HEADER [1306]", "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")

				elif myframe.encode('hex')[16] == '0' and myframe.encode('hex')[17] == '7':
					self.printAsProof("<----- GSMCMD_WAIT_DATA [1307]", "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")

				elif myframe.encode('hex')[16] == '5' and myframe.encode('hex')[17] == '7':#13 57
					self.printAsProof("<----- GSMCMD_GET_ECALL_DATA [1357]", "yellow")

					print("CONTROL  :  %s" %(myframe[10].encode('hex')))   #1
					print("VID      :  %s" %(myframe[11:31]))#20
					a1 = myframe[31].encode('hex')+myframe[32].encode('hex')+myframe[33].encode('hex')+myframe[34].encode('hex')
					t=int(a1,16)/1.0
					print  time.localtime(t)
					#print("Longitude  %f"%(int(a,16)/100000.))
					print("TIME     :  %s" %(myframe[31:35].encode('hex')))#4
					a1 = myframe[35].encode('hex')+myframe[36].encode('hex')+myframe[37].encode('hex')+myframe[38].encode('hex')
					t=int(a1,16)/3600000.0
					#print t
					print("LAT      :  %f" %(t))#4
					a1 = myframe[39].encode('hex')+myframe[40].encode('hex')+myframe[41].encode('hex')+myframe[42].encode('hex')
					t=int(a1,16)/3600000.0
					#print t
					print("LON      :  %f" %(t))#3
					print("DIR      :  %s" %(myframe[43].encode('hex')))   #4
					print("SERVER   :  %s" %(myframe[44:48].encode('hex'))) #4
					print("VAD      :  %s" %(myframe[48:48+102].encode('hex'))) #4

					self.printAsProof(myframe.encode('hex'), "yellow")

				elif myframe.encode('hex')[16] == 'a' and myframe.encode('hex')[17] == 'a':
					#print("RX--------------------------->:  %f  -- %d"%(ticks, self.frame_counter))
					#print("<-----_GSMDATA_SEND_DATA_ACK")
					self.printAsProof("<----- GSMDATA_SEND_DATA_ACK [13aa]", "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")

					if self.TXcardbinMode == True:
						self.dataAckResult = True
						print colored("Cardbin Ack received", "magenta")
					elif self.TXautotestMode == True:
						self.dataAckResult = True
						print colored("Autotest Ack received", "magenta")
					
					#if self.frame_counter == 0 :
					if self.responseNeeded:
						time.sleep(3) #Wait for the ack to be received first
						self.send_cmd_wait_data()

				elif myframe.encode('hex')[16] == 'a' and myframe.encode('hex')[17] == 'b':
					self.printAsProof("<----- GSMDATA_SLAVE_TO_MASTER [13ab]", "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")

					posHTTP = myframe.find("HTTP/1")
					if posHTTP >= 0 :
						posHTTP += len("HTTP/1") + 2
						self.httpResponseCode = int(myframe[posHTTP:posHTTP+4])
						self.printAsProof("HTTP response %d : %s"%(self.httpResponseCode, myframe[posHTTP+4:]), "yellow")
						
						self.responseNeeded = False
						self.HTTPattempts = 0


					a1=myframe[9].encode('hex')+myframe[10].encode('hex');#+myframe[41].encode('hex')+myframe[42].encode('hex')
					t=int(a1,16)
					if(t>0):
						if(self.RXpart == 0 and self.RXdataMode == True):
							myResponse = myframe[11:11+t]

							if len(myResponse.split('\r\n\r\n')) > 1:
								header = myResponse.split('\r\n\r\n')[0]

								data = myResponse.split('\r\n\r\n')[1]
								self.filebin.write(data)
							else:
								header = "No header ...."
								self.filebin.write(myResponse)

							print colored(header, 'magenta')
							elems = header.split('\r\n')
							for n in elems:
								if "Content-Length" in n:
									self.RXtotlen = int(n.split(" ")[1])
						elif(self.RXdataMode == True):
							self.filebin.write(myframe[11:11+t])

						self.RXpart += 1
						if self.RXtotlen > 0:
							self.printAsProof("GET : File part %d / %d ;; %d seconds elapsed"%(self.RXpart, self.RXtotlen / t, int(time.time()) - self.RXstart), "magenta")
							self.displayClass.UpdatePortion((self.RXpart*100)/(self.RXtotlen / t))
						else:
							self.printAsProof("GET : File part %d / %d ;; %d seconds elapsed"%(self.RXpart, self.RXtotlen / t, int(time.time()) - self.RXstart), "magenta")
							self.displayClass.UpdatePortion(0)
						
						#self.frame_counter+= 1
						if ("100 Continue" in myframe) and (self.TXcardbinMode == True or self.TXautotestMode == True):
							self.continueResult = True
							self.printAsProof("100 Continue", "yellow")
						else:
							self.send_cmd_wait_data()
					else:
						self.printAsProof("No data from slave", "yellow")

						if self.responseNeeded:
							self.HTTPattempts += 1
							if self.HTTPattempts > 3:
								self.responseNeeded = False
							else:
								time.sleep(1)
								self.send_cmd_wait_data()
				else:
					self.printAsProof("<----- UNKNOWN_FRAME", "yellow")
					self.printAsProof(myframe.encode('hex'), "yellow")
		else:
			#Not 128Prot Frame
			print myframe
			if mystate == self.STATE_WAIT or  mystate == self.STATE_CONNECTED:
				if "aed start" in myframe:
					self.printAsProof("Schiller GSM started : Boot time = %f s"%(time.time() - self.time_start), "magenta")

					self.send_cmd_mif()
					return self.STATE_MIF
				elif "CONNECT0" in myframe:
					print("CONNECTED--------------------> :  %f" %ticks)
		return mystate


	def printAsProof(self, line, color):
		print colored(line, color)
		self.consoleProofFile.write("[%d] %s\n"%(time.time() - self.time_start, line))

	def setDisplay(self, display):
		self.displayClass = display

	def launchModemProto(self, serial_port, mindelay, version):
		print colored("Schiller GSM testbench V%s\n"%(version), "magenta")

		if not os.path.exists("proof/"):
			print colored("No PROOF directory, create it", "red")
			os.makedirs("proof/")

		print 'Attempt establishing serial line connection...'
		self.serport = serial.Serial(serial_port, 115200, timeout=0.1)
		if not self.serport.isOpen():
			print colored('Unable to open serial line', 'red')
			return
		print colored(self.serport, 'green')
		self.time_start = time.time()

		self.TXdelay = mindelay

		print ("Start time = %f"%self.time_start)
		self.displayClass.UpdateConsolePrompt("[0] Schiller GSM testbench ID - %d \n"%(self.time_start))

		self.consoleProofFile = open("proof/%d_consoleProof.data"%(self.time_start), "wb")

		# Thread for keybord command
		keyboardThread = Thread(target=self.manage_command)
		keyboardThread.start()

		# Thread for GUI actions
		actionsThread = Thread(target=self.manage_orders)
		actionsThread.start()


		#Wait for "aed start"
		currstate = self.STATE_WAIT

		try:
			while True:
				response = self.read_frame()
				if len(response) > 0:
					currstate = self.manage_response(response, currstate)
					#if self.responseNeeded == True:
					#	self.responseNeeded = False
					#	self.send_cmd_wait_data()

		except KeyboardInterrupt:
			self.ActionShutdown()
			print("User request : interrupt received, exit")
			os._exit(-1)


	def ActionShutdown(self):
		if self.filebin != None:
			self.filebin.close()

		if self.consoleProofFile != None:
			self.consoleProofFile.close()

		print("User request : interrupt received, exit")
		os._exit(-1)

	def ActionActivateGPS(self):
		self.send_cmd_gps(1)

	def ActionPutKeepalive(self):
		self.orderToPerform = "TXKALIVE"

	def ActionPutCardbin(self):
		#self.PutRequest_SendFiles()
		self.orderToPerform = "TXCARDBIN"

	def ActionPostAutotest(self):
		#self.PutRequest_SendFiles()
		self.orderToPerform = "TXTEST"

	def ActionGetBinary(self):
		self.get_bin_file_proof()
		self.send_cmd_get_bin_file()

	def ActionGetConfig(self):
		self.send_cmd_get_xml_file()

	def ActionGetInfo(self):
		self.send_cmd_get_info()

	def ActionMakeVoiceCall(self):
		self.send_cmd_voicecall(1)

	def ActionMakeEcall(self):
		self.send_cmd_ecall(1)

	def ActionMakeSMS(self):
		self.send_cmd_sms()
