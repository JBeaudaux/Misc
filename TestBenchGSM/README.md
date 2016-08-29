# Schiller GSM testbench

* This program is designed to test the features of the Schiller GSM. It serves as a common ground to validate features both on Schiller and YTC side. 

* When a test sequence is started, the program decides of a test ID (the timestamp of the test start), and create a file called proof/ID_consoleProof.data . This file contains the test sequence details (all packets sent and received).

* When a HTTP(S) GET action is triggered, the requested file (FILENAME.bin) is first downloaded to the SEMA server from the desktop, and written into a file called proof/ID_Desktop_FILENAME.bin for later comparison. Then, the file is downloaded using the Schiller GSM, and written into a file called proof/ID_Device_FILENAME.bin . The two files can then be compared. If they are identical, the operation was successfull.

# Options

* --serialPort=xxxx to set the serial port to use for modem communication. Default is /dev/ttyUSB0.

* --noGUI to launch the program in console mode.

* --reqDelay=xxxx to set the minimum delay seperating two frames transmissions. Default is 300ms

# Bugs and Issues

In the GUI, commands in Green are functional and tested, in Orange are not fully tested, and in Red are buggy or non-working

* GET manifest command : Only part of the file is received ( 16056 bytes of data over 60210 bytes ), no HTTP header ( so no HTTP response code and content length )

# Changelog

* V1.0 - Initial release
