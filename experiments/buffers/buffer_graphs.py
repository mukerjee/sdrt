#!/usr/bin/env python

import sys
sys.path.insert(0, '..')
import os
import shelve
import glob
import numpy as np

from collections import defaultdict
from dotmap import DotMap
from simpleplotlib import plot
from parse_logs import parse_packet_log

SR = (1, 2)

types = ['static', 'resize', 'reTCP', 'reTCP+resize']

files = {
    'static': '/tmp/*-strobe-*-False-*-reno-*click.txt',
    'resize': '/tmp/*-QUEUE-True-*-reno-*click.txt',
    'reTCP': '/tmp/*-QUEUE-False-*-retcp-*click.txt',
    'reTCP+resize': '/tmp/*-QUEUE-True-*-retcp-*click.txt',
}

key_fn = {
    'static': lambda fn: int(fn.split('strobe-')[1].split('-')[0]),
    'resize': lambda fn: int(fn.split('True-')[1].split('-')[0]) / 20.0,
    'reTCP': lambda fn: 0,
    'reTCP+resize': lambda fn: int(fn.split('True-')[1].split('-')[0]) / 20.0,
}


def get_data(name):
    if name in db:
        return db[name]
    else:
        data = defaultdict(lambda: defaultdict(dict))
        for fn in glob.glob(sys.argv[1] + files[name]):
            key = key_fn[name](fn.split('/')[-1])
            _, lat, _, circ_util, _, _, _ = parse_packet_log(fn)
            data['lat'][50][key] = [x[1] for x in zip(*lat)[1]]
            data['lat'][99][key] = [x[1] for x in zip(*lat)[3]]
            data['circ_util'][key] = circ_util[SR]
        data['keys'] = list(zip(*sorted(data['circ_util'].items()))[0])
        data['lat'][50] = list(zip(*sorted(data['lat'][50].items()))[1])
        data['lat'][99] = list(zip(*sorted(data['lat'][99].items()))[1])
        data['circ_util'] = list(zip(*sorted(data['circ_util'].items()))[1])
        return dict(data)


def graph_lat(keys, latencies, fn):
    x = [keys for i in xrange(len(latencies[0]))]
    y = zip(*latencies)

    options = DotMap()
    options.plot_type = 'LINE'
    options.legend.options.labels = ['All traffic', 'Only circuit',
                                     'Only packet']
    options.legend.options.fontsize = 19
    options.series_options = [DotMap(marker='o', markersize=10, linewidth=5)
                              for i in range(len(x))]
    options.output_fn = 'graphs/%s_vs_latency.pdf' % fn
    options.x.label.xlabel = 'Buffer size (packets)' if 'static' in fn \
                             else 'Early buffer resize ($\mu$s)'
    options.y.label.ylabel = 'Median latency ($\mu$s)'
    options.x.ticks.major.labels = DotMap(
        locations=[4, 8, 16, 32, 64, 128]) if 'static' in fn \
        else DotMap(locations=[0, 200, 400, 600, 800, 1000, 1200, 1400])
    options.y.ticks.major.labels = DotMap(
        locations=[0, 100, 200, 300, 400, 500, 600])
    options.y.limits = [0, 600]
    plot(x, y, options)


def graph_circuit_util(util, fn):
    x = [np.arange(len(util))]
    y = [map(lambda j: min(j / (0.9 * 1.0/7 * 80) * 100, 100.0), util)]

    options = DotMap()
    options.plot_type = 'BAR'
    options.legend.options.fontsize = 12
    options.bar_labels.format_string = '%1.0f'
    options.bar_labels.options.fontsize = 25
    options.output_fn = 'graphs/%s_vs_circuit_util.pdf' % fn
    options.x.label.xlabel = 'Buffer size (packets)' if 'static' in fn \
                             else 'Early buffer resize ($\mu$s)'
    options.y.label.ylabel = 'Avg. circuit utilization (%)'
    options.x.ticks.major.labels = DotMap(
        text=[4, 8, 16, 32, 64, 128]) if 'static' in fn \
        else DotMap(text=[0, 200, 400, 600, 800, 1000, 1200, 1400])
    options.y.ticks.major.show = False
    options.x.ticks.major.show = False
    plot(x, y, options)


def graph_util_vs_latency(utils, latencies, fn):
    x = [map(lambda j: min(j / (0.9 * 1.0/7 * 80) * 100, 100.0), u)
         for u in utils]
    y = [zip(*l)[0] for l in latencies]

    options = DotMap()
    options.plot_type = 'LINE'
    options.legend.options.labels = ['Static buffers (vary size)',
                                     'Dynamic buffers (vary $\\tau$)',
                                     'reTCP',
                                     'reTCP + dynamic buffers (vary $\\tau$)']
    options.legend.options.fontsize = 19
    options.series_options = [DotMap(marker='o', markersize=10, linewidth=5)
                              for i in range(len(x))]
    options.series_options[2].marker = 'x'
    options.series_options[2].s = 100
    del options.series_options[2].markersize
    options.series_options[2].zorder = 10
    options.output_fn = 'graphs/throughput_vs_latency99.pdf' if '99' in fn \
                        else 'graphs/throughput_vs_latency.pdf'
    options.x.label.xlabel = 'Circuit utilization (%)'
    options.y.label.ylabel = '99th percent. latency ($\mu$s)' if '99' in fn \
                             else 'Median latency ($\mu$s)'
    options.y.limits = [0, 1000] if '99' in fn else [0, 600]
    options.y.ticks.major.labels = DotMap(
        locations=[0, 200, 400, 600, 800, 1000]) if '99' in fn else \
        DotMap(locations=[0, 100, 200, 300, 400, 500, 600])

    plot(x, y, options)


if __name__ == '__main__':
    if not os.path.isdir(sys.argv[1]):
        print 'first arg must be dir'
        sys.exit(-1)
    db = shelve.open(sys.argv[1] + '/buffer_shelve.db')

    typ = 'static'
    db[typ] = get_data(typ)
    graph_lat(db[typ]['keys'], db[typ]['lat'][50], typ)
    graph_circuit_util(db[typ]['circ_util'], typ)

    typ = 'resize'
    db[typ] = get_data(typ)
    graph_lat([0] + db[typ]['keys'],
              [db['static']['lat'][50][2]] + db[typ]['lat'][50], typ)
    graph_circuit_util([db['static']['circ_util'][2]] + db[typ]['circ_util'],
                       typ)

    typ = 'reTCP'
    db[typ] = get_data(typ)

    typ = 'reTCP+resize'
    db[typ] = get_data(typ)

    utils = [db[t]['circ_util'] for t in types]
    lat50 = [db[t]['lat'][50] for t in types]
    lat99 = [db[t]['lat'][99] for t in types]
    graph_util_vs_latency(utils, lat50, '50')
    graph_util_vs_latency(utils, lat99, '99')

    db.close()
