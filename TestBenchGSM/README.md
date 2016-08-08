# Schiller GSM testbench

* This program is designed to test the features of the Schiller GSM. It serves as a common ground to validate features both on Schiller and YTC side. 

* When a test sequence is started, the program decides of a test ID (the timestamp of the test start), and create a file called proof/ID_consoleProof.data . This file contains the test sequence details (all packets sent and received).

* When a HTTP(S) GET action is triggered, the requested file (FILENAME.bin) is first downloaded to the SEMA server from the desktop, and written into a file called proof/ID_Desktop_FILENAME.bin for later comparison. Then, the file is downloaded using the Schiller GSM, and written into a file called proof/ID_Device_FILENAME.bin . The two files can then be compared. If they are identical, the operation was successfull.

# Changelog

* V1.0 - Initial release
