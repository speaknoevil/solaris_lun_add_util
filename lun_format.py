#!/usr/bin/python
#
# Created: 20180314 #Pi Day
# Designed around solaris 11 with python 2.7.
""" Takes a list of luns and formats them (on Solaris); optionally chowns to specific oracle user/grp """

import os
import sys
import argparse
from subprocess import *
import re
import logging

def arg_handler():
    parser = argparse.ArgumentParser(description=r'[Solaris] Given a label, add any new luns, and potentially chown for oracle use.')
    parser.add_argument('label', type=str, help=r'Assigns label to any new luns. 8 char max')
    parser.add_argument('-c', '--chown', action='store_true', help=r'Optionally sets new lun permissions to oracle:dba')
    parser.add_argument('-q', '--quiet', action='store_true', help=r'Minimize output')
    parser.add_argument('--debug', action='store_true', help='Turn on debug')
    return parser.parse_args()

def exception_handler():
    return '{}. {}, line: {}'.format(sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)


class LunFormat:
    diskRoot = '/dev/rdsk/'
    OS = sys.platform[:3]
    rawLunformat = r"""l
0
y
vo
REPLACEME
y
p
m
1










REPLACEME
y
p
6


34

l
0
y
q
q"""

    def OS_check(self):
        if self.OS != 'sun':
            print(' Error: Not Solaris')
            sys.exit(2)

    def ch_dir(self):
        try:
            os.chdir(self.diskRoot)
        except Exception as e:
            print(' unable to chdir to ' + self.diskRoot)
            logging.critical(exception_handler())
            sys.exit(2)

def log_config(args):
    """ For dev, not really general logging. """
    if args.debug: logging.basicConfig(level=logging.DEBUG)

def proc_printer(Tuple):
    for o, e in Tuple:
        print(o.decode('utf-8'))
        if e: print(e)

def scan():
    """ Scans for new luns """
    scan_cmd = ['/usr/sbin/sudo', '/usr/sbin/cfgadm', '-al']
    format_cmd = ['/usr/sbin/sudo', '/usr/sbin/format']
    newDiskPat = re.compile(r'(c0t6\w{31}d0):\s+configured with capacity')
    try:
        cfgadm_proc = Popen(scan_cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        cfgadm_out = cfgadm_proc.communicate()
        format_proc = Popen(format_cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        format_out= format_proc.communicate()
        controller_list = newDiskPat.findall(format_out[0])
        if controller_list:
            return controller_list
    except Exception as e:
        print(' Error: Failed to collect disk names')
        logging.critical(exception_handler())
        sys.exit(2)

def lun_format_input(raw_template,label):
    logging.debug('Verifying label input')
    alphanumCheck = re.search(r'^\w+$', label)
    if alphanumCheck and len(label) < 9:
        replacement = label
    else:
        print(' Error: disk label format incorrect.')
        sys.exit(1)
    return re.sub(r'REPLACEME', replacement, raw_template)

def format_luns(lun_list, lun_format):
    """ Formats given list of disks """
    logging.debug('--{Formatting luns}--')
    for x in lun_list:
        x = x.strip()
        print(' Formatting:\t' + x)
        cmd1 = ['/usr/bin/sudo', '/usr/sbin/format', '-e', x]
        format_p1 = Popen(cmd1, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        Output_t = format_p1.communicate(input=lun_format)
        proc_printer(Output_t)

def check_luns(lun_list):
    """ Prints out format info to allow you to check that Luns are correctly formatted """
    logging.debug('Verifying luns post format')
    for x in lun_list:
        x = x.strip()
        x = x + 's6'
        print(' Verifying:\t' + x)
        cmd2 = ['/usr/bin/sudo', '/usr/sbin/format', '-e', x]
        format_p2 = Popen(cmd2, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        ver_output = format_p2.communicate(input='verify\n')
        for line in ver_output[0].split('\n'):
            if re.search('Volume name|usr', line):
                print(line)

def ticket_print(lun_list,disk_root):
    """ Prints disk info that can be pasted into jira """
    logging.debug('Path to new luns:')
    for x in lun_list: print(disk_root + x.strip() + 's6')

def chown_handler(lun_list,args):
    if args.chown:
        if args.quiet:
            chown_files(lun_list, verbose=False)
        else:
            chown_files(lun_list)

def lun_file_list(lunlist):
    """ Does a long ls on the actual device file """
    myLunList = []
    for x in lunlist:
        x = x.strip()
        x = x + 's6'
        cmd1 = ['/usr/bin/ls', '-l', x]
        ls_p1 = Popen(cmd1, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        ls_p1Stdout = ls_p1.communicate()[0]
        lsp1Stdout_split = ls_p1Stdout.split(' ')[-1].strip()
        myLunList.append(lsp1Stdout_split)
    return myLunList

def lslLuns(lun_files_list):
    """ Does a long ls LUNs """
    for y in lun_files_list:
        cmd1 = ['/usr/bin/ls', '-l', y]
        ls_p2 = check_output(cmd1, stderr=STDOUT)
        print ls_p2.strip()

def chownLuns(lun_files_list):
    """ Chowns luns to oracle:dba """
    for y in lun_files_list:
        cmd1 = ['/usr/bin/sudo', '/bin/chown', 'oracle:dba', y]
        choProc1 = check_output(cmd1, stderr=STDOUT)

def chown_files(lunlist, verbose=True):
    """ Call this with a list of luns to do the actual chown. Lists files before and after. """
    s6_luns = lun_file_list(lunlist)
    if verbose:
       print '-={Before}=-:'
       lslLuns(s6_luns)
    chownLuns(s6_luns)
    if verbose:
        print '-={After }=-:'
        lslLuns(s6_luns)

def main():
    """ real format ; check formatting ; print ticket output """
    args = arg_handler()
    myLF = LunFormat()
    scan() #moo
    myLF.OS_check()
    myLF.ch_dir()
    log_config(args)
    myDiskroot = myLF.diskRoot
    myLunFormat = lun_format_input(myLF.rawLunformat,args.label)
    myLunList = scan()
    format_luns(myLunList,myLunFormat)
    chown_handler(myLunList,args)
    check_luns(myLunList)
    ticket_print(myLunList,myDiskroot)

if __name__ == '__main__':
    main()
