This directory contains all the logs and test results from the Schiller GSM testbench operations. 

Each file is named with a timestamp as a prefix. This is the timestamp of the test performed (it is the same for all operations of a single test).
* For download operations, the timestamp is followed by "Desktop" or "Device". "Desktop" means the file was downloaded from the desktop machine using etherned direct HTTP request (it is the "goal" to achieve). "Device" means the file was downloaded using the Schiller GSM via the 128PROT protocol.

A python script is also available to compare XML and BIN files