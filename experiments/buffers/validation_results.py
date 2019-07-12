#!/usr/bin/env python

import sys
sys.path.insert(0, '..')
import os
import glob

from parse_logs import parse_validation_log

    
if __name__ == '__main__':
    if not os.path.isdir(sys.argv[1]):
        print 'first arg must be dir'
        sys.exit(-1)
    parse_validation_log(
        sys.argv[1],
        glob.glob(sys.argv[1] + '/*-validation-no_circuit-*-flowgrind.txt'))
    parse_validation_log(
        sys.argv[1],
        glob.glob(sys.argv[1] + '/*-validation-circuit-*-flowgrind.txt'))
