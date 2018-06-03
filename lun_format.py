#!/usr/bin/python
#
# Author: Shane Boone
# Created: 20180314 #Pi Day
#
# Designed around solaris 11 with python 2.7.
""" Scans for any newly zoned luns and formats them (on Solaris); optionally chowns to specific oracle user/grp """

from __future__ import print_function
import os
import sys
import argparse
from subprocess import *
import re
import logging

def arg_handler():
    ver_help=r'Runs a verification of lun arguments, then exits. e.g. lun_format.py ver --verify c0t60060E8007DF23000030DF23000000CFd0 c0t60060E8007DF23000030DF23000000CGd0'
    sh_ch_help=r'Chowns shared disks on a secondary dbs given a list of luns. e.g. lun_format.py shared --shared_chown c0t60060E8007DF23000030DF23000000CFd0 c0t60060E8007DF23000030DF23000000CGd0'
    parser = argparse.ArgumentParser(description=r'[Solaris] Given a label, add any new luns, and potentially chown for oracle use. See README.md on github')
    parser.add_argument('label', type=str, help=r'Assigns label to any new luns. 8 char max. Required to run. Use "ver" for verify.')
    parser.add_argument('-c', '--chown', action='store_true', help=r'Optionally sets new lun permissions to oracle:dba')
    parser.add_argument('--shared_chown', nargs='+', type=str, help=sh_ch_help)
    parser.add_argument('--verify', nargs='+', type=str, help=ver_help)
    parser.add_argument('-q', '--quiet', action='store_true', help=r'Minimize output of chown.')
    parser.add_argument('--ownership', default='oracle:dba', type=str, help=r'Change default user:group for chown')
    parser.add_argument('--logfile_path', default='/var/tmp/', type=str, help=r'Change default directory to store log file. Must be writeable by your user.')
    parser.add_argument('--debug', action='store_true', help=r'Turn on debug. Only way to see raw format command output. Outputs to log.')
    return parser.parse_args()

def exception_handler():
    return '{}. {}, line: {}'.format(sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2].tb_lineno)

class LunFormat(object):
    ''' Base/Parent class '''
    def __init__(self):
        self.disk_root = '/dev/rdsk/'
        self.OS = sys.platform[:3]
        self.raw_format_input = r"""l
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
        ''' Can only be run on solaris hosts '''
        if self.OS != 'sun':
            print(' Error: Not Solaris')
            sys.exit(2)

    def ch_dir(self):
        ''' Move to working directory '''
        try:
            os.chdir(self.disk_root)
        except Exception as e:
            print(' unable to chdir to ' + self.disk_root)
            logging.critical(exception_handler())
            sys.exit(2)


class Lun(LunFormat):
    ''' Individual lun objects '''
    def __init__(self,lun,label):
        super(Lun, self).__init__()
        self.lun_id = lun
        self.label = label
        logging.info('Starting format work on {s.lun_id} with label: {s.label}'.format(s=self))
        self.lun_format_input = lun_format_input(self.raw_format_input,self.label)
        self.device = 'chown not run.'
        self.dev_before = 'None'
        self.dev_after = 'None'
        self.format_output = 'format not run.'
        self.verification = 'Verification not run.'
        self.ticket_path = str(os.path.join(self.disk_root, self.lun_id) + 's6')

    def __repr__(self):
        return '{s.lun_id}, {s.label}, {s.format_output}, {s.device}, {s.dev_before}, {s.dev_after}, {s.verification}, {s.ticket_path}'.format(s=self)

    def __str__(self):
        a = [ 'LUN ID: {s.lun_id}', 'LABEL: {s.label}', 'LUN DEVICE FILE: {s.device}', 'LUN DEVICE FILE OWNERSHIP BEFORE CHOWN: {s.dev_before}' ]
        b = [ 'LUN DEVICE FILE OWNERSHIP AFTER CHOWN: {s.dev_after}', 'PERTINENT LUN "format verify" INFORMATION: {s.verification}' ]
        c = [ 'LUN ABSOLUTE PATH: {s.ticket_path}' ]
        return '\n'.join(a + b + c).format(s=self)


def log_config(args):
    """ General logging goes to console/stderr and a log file. Debug for dev or verbose output. """
    try:
        logPath = args.logfile_path
    except Exception as e:
        print(' Error: Unable to set logPath ' + args.logfile_path)
        logging.critical(exception_handler())
        sys.exit(2)
    fileName = re.findall('(\w+).py', sys.argv[0])[0]
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    rootLogger = logging.getLogger()
    #-------------------------------
    fileHandler = logging.FileHandler("{0}/{1}.log".format(logPath, fileName))
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)
    #-------------------------------
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

def scan():
    """ Scans for new luns and returns a list of lun IDs"""
    scan_cmd = ['/usr/bin/sudo', '/usr/sbin/cfgadm', '-al']
    format_cmd = ['/usr/bin/sudo', '/usr/sbin/format']
    newDiskPat = re.compile(r'(c0t6\w{31}d0):\s+configured with capacity')
    logging.debug(' About to run: "{}"'.format(' '.join(scan_cmd)))
    logging.debug(' About to run: "{}"'.format(' '.join(format_cmd)))
    try:
        cfgadm_proc = Popen(scan_cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        cfgadm_out = cfgadm_proc.communicate()
        format_proc = Popen(format_cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE)
        format_out = format_proc.communicate()
        controller_list = newDiskPat.findall(format_out[0])
        if controller_list and controller_list[0] != None:
            return controller_list
    except Exception as e:
        print(' Error: Failed to collect disk names')
        logging.critical(exception_handler())
        sys.exit(2)

def input_check(input_type,Input):
    ''' Verifies labels or lun names '''
    if input_type == 'label':
        logging.debug('Verifying label input')
        alphanumCheck = re.search(r'^\w+$', Input)
        if alphanumCheck and len(Input) < 9:
            return Input
        else:
            print(' Error: disk label format incorrect.')
            sys.exit(1)
    elif input_type == 'lun':
        logging.debug('Verifying lun id input')
        if len(Input) > 30:
            logging.critical(' Error: List of luns too large.')
            sys.exit(2)
        luns_d = dict(enumerate(Input))
        for pos in xrange(len(luns_d)):
            inputCheck = re.search(r'^\w{37}$', luns_d[pos])
            if inputCheck:
                pass
            else:
                logging.error(r' Error: Lun name failed input format check')
                sys.exit(2)
    else:
        logging.error(r' Error: Invalid input format type.')
        sys.exit(2)

def lun_format_input(raw_template,label):
    ''' Updates raw format input with label name '''
    logging.debug('Creating format input template')
    replacement = input_check('label',label)
    return re.sub(r'REPLACEME', replacement, raw_template)

def format_lun(lunobj):
    """ Surprise: formats given lun """
    lun = lunobj.lun_id
    logging.debug(' --{Formatting lun}--\t' + lun)
    cmd1 = ['/usr/bin/sudo', '/usr/sbin/format', '-e', lun]
    logging.debug(' About to run: "{}"'.format(' '.join(cmd1)))
    format_p1 = Popen(cmd1, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    lunobj.format_output = format_p1.communicate(input=lunobj.lun_format_input)[0]

def verify_handler(lunobj,args):
    ''' Determines if a separate lun verify needs to be run '''
    if args.verify:
        verify_luns(lunobj,args.verify)
        sys.exit(0)

def verify_luns(lunobj,*lun_list):
    """ Prints out format info to allow you to check that the lun is correctly formatted """
    logging.debug('Verifying lun(s) formatting')
    input_check('lun',lun_list[0])
    verification = []
    for x in xrange(len(lun_list[0])):
        my_lun = lun_list[0][x] + 's6'
        logging.info(' Verifying:\t' + my_lun)
        cmd2 = ['/usr/bin/sudo', '/usr/sbin/format', '-e', my_lun]
        logging.debug(' About to run: "{}"'.format(' '.join(cmd2)))
        format_p2 = Popen(cmd2, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        ver_output = format_p2.communicate(input='verify\n')[0]
        for line in ver_output.split('\n'):
            if re.search('Volume name|usr', line):
                logging.info(line)
                verification.append(line)
        lunobj.verification = verification

def shared_chown_handler(args):
    ''' Determines if a separate lun chown (shared luns?) needs to be run '''
    if args.shared_chown:
        shared_chown(args.label,args.ownership,args.shared_chown)
        sys.exit(0)

def shared_chown(label,ownership,*lun_list):
    """ Used to chown secondary dbs luns to oracle:dba  """ 
    logging.info('Chowning shared lun(s) {}'.format(str(lun_list)))
    input_check('lun',lun_list[0])
    myLF = LunFormat()
    myLF.ch_dir()
    luns_d = dict(enumerate(lun_list[0]))
    lunobj_d = {}
    for pos in xrange(len(luns_d)):
        my_lun = luns_d[pos]
        lunobj_d[my_lun] = Lun(my_lun,label)
        chown_file(lunobj_d[my_lun],ownership,verbose=False)
        logging.debug(repr(lunobj_d[my_lun]))
    logging.info(' -=[Before]=-')
    [ logging.info('{lo.lun_id}:{lo.dev_before}'.format(lo=lunobj_d[key])) for key in lunobj_d.keys() ]
    logging.info(' -=[After]=-')
    [ logging.info('{lo.lun_id}:{lo.dev_after}'.format(lo=lunobj_d[key])) for key in lunobj_d.keys() ]
    sys.exit(0)

def chown_handler(lun_obj,args):
    ''' Got chown? '''
    if args.chown:
        if args.quiet:
            chown_file(lun_obj, args.ownership, verbose=False)
        else:
            chown_file(lun_obj, args.ownership)

def chown_file(lun_obj, ownership, verbose=True):
    """ Call this with a lun object to do the actual chown. Lists device file before and after. """
    get_lun_devfile(lun_obj)
    lun_obj.dev_before = lslLun(lun_obj.device)
    #---
    cmd1 = ['/usr/bin/sudo', '/bin/chown', ownership, lun_obj.device]
    logging.debug(' About to run: "{}"'.format(' '.join(cmd1)))
    try:
        chown_p1 = Popen(cmd1, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        chown_p1_out = chown_p1.communicate()[0]
    except Exception as e:
        print(' Error: Unable to chown ' + lun_obj.device)
        logging.critical(exception_handler())
        sys.exit(2)
    #/---
    lun_obj.dev_after = lslLun(lun_obj.device)
    if verbose:
        logging.info('[Before]: {lo.dev_before}'.format(lo=lun_obj))
        logging.info('[After ]: {lo.dev_after}'.format(lo=lun_obj))

def get_lun_devfile(lun_obj):
    """ Determines device file by looking at the symlink of the Lun ID """
    lun = lun_obj.lun_id + 's6'
    cmd1 = ['/usr/bin/ls', '-l', lun]
    logging.debug(' About to run: "{}"'.format(' '.join(cmd1)))
    try:
        ls_p1 = Popen(cmd1, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        ls_p1_stdout = ls_p1.communicate()[0]
    except Exception as e:
        print(' Error: Unable to ls ' + lun_obj.disk_root + lun + '. Verify it exist.')
        logging.critical(exception_handler())
        sys.exit(2)
    lun_obj.device = ls_p1_stdout.split(' ')[-1].strip()

def lslLun(lun_dev):
    """ Does a long ls on device file """
    cmd1 = ['/usr/bin/ls', '-l', lun_dev]
    ls_p2 = Popen(cmd1, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    return ls_p2.communicate()[0].strip()

def standard_run(args):
    ''' Finds any new luns; formats; possible chown; verify ; print path '''
    myLunList = scan()
    luns_d = {}
    for pos in xrange(len(myLunList)):
        my_lun = myLunList[pos]
        luns_d[my_lun] = Lun(my_lun, args.label)
        format_lun(luns_d[my_lun])
        chown_handler(luns_d[my_lun],args)
    logging.info('Verifying lun(s)')
    [ verify_luns(luns_d[lunkey],[luns_d[lunkey].lun_id]) for lunkey in luns_d.keys() ]
    logging.info('Listing lun path(s) for ticket')
    [ print(luns_d[lunkey].ticket_path) for lunkey in luns_d.keys() ]
    [ logging.info(str(luns_d[lunkey])) for lunkey in luns_d.keys() ]
    [ logging.debug(repr(luns_d[lunkey])) for lunkey in luns_d.keys() ]

def main():
    ''' Verifies environment; Determines which function to perform '''
    args = arg_handler()
    myLF = LunFormat()
    myLF.OS_check()
    myLF.ch_dir()
    log_config(args)
    verify_handler(myLF,args)
    shared_chown_handler(args)
    standard_run(args)

if __name__ == '__main__':
    main()
