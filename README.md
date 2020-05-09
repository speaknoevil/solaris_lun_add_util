# san_utils

NOTE: Currently does not function with Solaris 11.4 due to changes in 'format' output.

Client side LUN addition utility for Solaris hosts. Primary use is for oracle lun additions.

The primary use of this program is for is discovering newly zoned luns on solaris servers, formatting them, optionally chowning them to oracle:dba,
listing format info afterward to verify labels/size, and finally listing the new luns to paste into your ticketing system. 
This is to be run as a non-privileged user, and expects sudo access.

Example of a standard use including chown:
./lun_format.py psdata -c

Pertinent info from the run can be found in the log.


In addition to the standard use, I have included two functions that perform tasks that would be needed outside of a new lun scenario.
Rather than create a suite of separate files that would inherit from lun_format I wanted to keep management of this simple by keeping it at one file. 
KISS

The first function is "shared_chown", which would be useful for db servers that share the same luns, and need their ownership changed.

The second is "verify", which can run the verify function on existing luns.

Both of these functions work in a similar fashion. You will need to provide a label name because it is a requirement for this program to run.
In both of these instances you can use any text that fits a standard label format. Suggestions are given in the examples. Next, you'll need
to provide a lun name or names (up to 30). Do not include slices.

Examples:

lun_format.py ver --verify c0t60060E8007DF23000030DF23000000CFd0 c0t60060E8007DF23000030DF23000000CGd0

lun_format.py shared --shared_chown c0t60060E8007DF23000030DF23000000CFd0 c0t60060E8007DF23000030DF23000000CGd0

The output of this program will show on stderr, and log to a file (defaults to /var/tmp/lun_format.log).
