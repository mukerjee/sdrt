#!/usr/bin/env python

import adu_common

import sys
sys.path.insert(0, '/etalon/experiments')
from common import initializeExperiment, finishExperiment, flowgrind
from click_common import setConfig

adu_common.CONFIGS.append({'packet_log': False,
                           'type': 'fixed',
                           'traffic_source': 'ADU',
                           'fixed_schedule': '2 39600 7/0/1/2/3/4/5/6 400 -1/-1/-1/-1/-1/-1/-1/-1'})

for config in adu_common.CONFIGS:
    if config['traffic_source'] == 'ADU':
        initializeExperiment('flowgrindd_adu')
    else:
        initializeExperiment('flowgrindd')

    print '--- running test type %s...' % config
    setConfig(config)
    print '--- done...'

    settings = {'big_and_small': True}
    flowgrind(settings)

finishExperiment()
