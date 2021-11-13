from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
import time

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3
	
	# Initiation..
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.expFrameNbr = 0
		self.statPacketsLost = 0
		self.statTotalBytes = 0
		self.statTotalPlayTime = 0
		self.startTime = 0
		self.totalFrames = 0
		
	# THIS GUI IS JUST FOR REFERENCE ONLY, STUDENTS HAVE TO CREATE THEIR OWN GUI 	
	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Play button		
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 

		#Create labels to display statistics about the session
		self.displays = []
		for i in range(6):
			DLabel = Label(self.master, height=1)
			DLabel.grid(row=2 + i, column=0, columnspan=4, sticky=W, padx=5, pady=5) 
			self.displays.append(DLabel)
	
	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)
	#TODO
	
	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN) #Lo ben server	
		#Xu ly ben client
		self.master.destroy() # Dong GUI
		os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Xoa cache
	#TODO

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
	#TODO
	
	def playMovie(self):
		"""Play button handler."""
		if self.state == self.READY:
			# Tao mot thread moi de nhan packet
			self.startTime = time.time()
			threading.Thread(target=self.listenRtp).start()
			self.playEvent = threading.Event()
			self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)
	#TODO
	
	def listenRtp(self):		
		"""Listen for RTP packets."""
		while True:
			try:
				data, addr = self.rtpSocket.recvfrom(16384)

				if data: #Neu thanh cong thi decode du lieu va xu ly
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)

					self.expFrameNbr += 1
					currFrameNbr = rtpPacket.seqNum()					
					print("Current Seq Num: " + str(currFrameNbr))

					if currFrameNbr > self.frameNbr: # Discard the late packet
						self.frameNbr = currFrameNbr
						payload = rtpPacket.getPayload()
						self.updateMovie(self.writeFrame(payload))
						self.totalFrames += 1

					if self.expFrameNbr != currFrameNbr: #Compare ecpected frame number and gotten frame number
						self.statPacketsLost += 1
					
					# Calculate total data received 
					payload_length = len(payload)
					self.statTotalBytes += payload_length
					
					# Calculate total play time of the session
					curTime = time.time()
					self.statTotalPlayTime += curTime - self.startTime
					self.operationTime = curTime - self.startTime
					self.startTime = curTime

					# Display the statistics about the session
					self.displays[0]["text"] = 'Current frame: ' + str(currFrameNbr)
					self.displays[1]["text"] = 'Frame per second (fps): ' + str(format(1/self.operationTime,".2f")) + '\t\tAverage: ' + str(format(self.totalFrames/self.statTotalPlayTime,".2f"))
					self.displays[2]["text"] = 'Data received: ' + str(self.statTotalBytes) + ' bytes'
					self.displays[3]["text"] = 'Data Rate: ' + str(format(payload_length / self.operationTime,".2f")) + ' bytes/s'  + '\t\tAverage: ' + str(format(self.statTotalBytes / self.statTotalPlayTime,".2f")) + ' bytes/s'
					self.displays[4]["text"] = 'Packets Lost: ' + str(self.statPacketsLost) + ' packets'
					self.displays[5]["text"] = 'Packets Lost Rate: ' + str(float(self.statPacketsLost / currFrameNbr))

			except:
				# Stop listening upon requesting PAUSE or TEARDOWN
				if self.playEvent.isSet():
					break

				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break
		#TODO
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT

		file = open(cachename, "wb")
		file.write(data)
		file.close()

		return cachename
	#TODO
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image = photo, height=288) 
		self.label.image = photo

	#TODO
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			tkinter.messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
	#TODO
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		#-------------
		# TO COMPLETE
		#-------------
		if requestCode == self.SETUP and self.state == self.INIT:
			threading.Thread(target=self.recvRtspReply).start()
			# Update RTSP sequence number.
			self.rtspSeq += 1

			# Write the RTSP request to be sent.
			request = 'SETUP ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nTransport: RTP/UDP; client_port= ' + str(self.rtpPort)

			# Keep track of the sent request.
			self.requestSent = self.SETUP

		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			self.rtspSeq += 1
			request = 'PLAY ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)
			self.requestSent = self.PLAY

		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			self.rtspSeq += 1
			request = 'PAUSE ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)
			self.requestSent = self.PAUSE

		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			self.rtspSeq += 1
			request = 'TEARDOWN ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(self.sessionId)
			self.requestSent = self.TEARDOWN
		else:
			return

		self.rtspSocket.send(request.encode('utf-8'))
		print("Data sent:\n" + request)
		
	
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)

			if reply:
				self.parseRtspReply(reply.decode())

			# # Neu gui Teadown thi dong RTSP socket lai luon
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break
		#TODO
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""

		lines = data.split('\n')
		seqNum = int(lines[1].split(' ')[1])

		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session

			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200:
					if self.requestSent == self.SETUP:
						self.state = self.READY
						self.openRtpPort()

					elif self.requestSent == self.PLAY:
						self.state = self.PLAYING

					elif self.requestSent == self.PAUSE:
						self.state = self.READY

						# The play thread exits. A new thread is created on resume.
						self.playEvent.set()

					elif self.requestSent == self.TEARDOWN:
						# self.state = ...
						self.state = self.INIT
						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1
		#TODO
	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		#-------------
		# TO COMPLETE
		#-------------
		# Create a new datagram socket to receive RTP packets from the server
		self.rtpSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

		# Set the timeout value of the socket to 0.5sec
		self.rtpSocket.settimeout(0.5)
		try:
			self.rtpSocket.bind((self.serverAddr,self.rtpPort)) 

		except:
			tkinter.messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' % self.rtpPort)
		

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		#1 Dung video neu dang chieu
		#2. Hoi co muon dong that khong va xu ly tung truong hop
		self.pauseMovie()
		if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
		else:
			threading.Thread(target=self.listenRtp).start()
			self.sendRtspRequest(self.PLAY)
		#TODO
