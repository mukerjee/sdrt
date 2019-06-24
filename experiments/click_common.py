import socket
import time
import common

import sys
sys.path.insert(0, '/etalon/etc')
from python_config import NUM_RACKS, TIMESTAMP, SCRIPT, TDF, EXPERIMENTS, \
    CLICK_ADDR, CLICK_PORT, CLICK_BUFFER_SIZE, DEFAULT_CIRCUIT_CONFIG

CLICK_SOCKET = None
CURRENT_CONFIG = {}
FN_FORMAT = ''


def initializeClickControl():
    global CLICK_SOCKET
    print '--- connecting to click socket...'
    CLICK_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    CLICK_SOCKET.connect((CLICK_ADDR, CLICK_PORT))
    CLICK_SOCKET.recv(CLICK_BUFFER_SIZE)
    print '--- done...'


def clickWriteHandler(element, handler, value):
    message = "WRITE %s.%s %s\n" % (element, handler, value)
    print message.strip()
    CLICK_SOCKET.send(message)
    print CLICK_SOCKET.recv(CLICK_BUFFER_SIZE).strip()


def clickReadHandler(element, handler):
    message = "READ %s.%s\n" % (element, handler)
    print message.strip()
    CLICK_SOCKET.send(message)
    # The return value is three lines. The last line is the actual value.
    data = int(CLICK_SOCKET.recv(CLICK_BUFFER_SIZE).strip().split("\n")[-1])
    print data
    return data


def setLog(log):
    print 'changing log fn to %s' % log
    clickWriteHandler('hsl', 'openLog', log)
    if log != '/tmp/hslog.log':
        EXPERIMENTS.append(log)
    time.sleep(0.1)


def disableLog():
    print 'diabling packet logging'
    clickWriteHandler('hsl', 'disableLog', '')
    time.sleep(0.1)


def setQueueSize(size):
    for i in xrange(1, NUM_RACKS+1):
        for j in xrange(1, NUM_RACKS+1):
            clickWriteHandler('hybrid_switch/q%d%d/q' % (i, j),
                              'capacity', size)


def setEstimateTrafficSource(source):
    clickWriteHandler('traffic_matrix', 'setSource', source)


def setInAdvance(in_advance):
    clickWriteHandler('runner', 'setInAdvance', in_advance)


def setQueueResize(b):
    if b:
        clickWriteHandler('runner', 'setDoResize', 'true')
    else:
        clickWriteHandler('runner', 'setDoResize', 'false')
    time.sleep(0.1)


def getCounters():
    circuit_bytes = []
    packet_up_bytes = []
    packet_down_bytes = []
    for i in xrange(1, NUM_RACKS+1):
        circuit_bytes.append(
            clickReadHandler('hybrid_switch/circuit_link%d/lu' % (i),
                             'total_bytes'))
        packet_up_bytes.append(
            clickReadHandler('hybrid_switch/packet_up_link%d/lu' % (i),
                             'total_bytes'))
        packet_down_bytes.append(
            clickReadHandler('hybrid_switch/ps/packet_link%d/lu' % (i),
                             'total_bytes'))
    return (circuit_bytes, packet_up_bytes, packet_down_bytes)


def clearCounters():
    for i in xrange(1, NUM_RACKS+1):
        for j in xrange(1, NUM_RACKS+1):
            clickWriteHandler('hybrid_switch/q%d%d/q' % (i, j),
                              'clear', "")
        clickWriteHandler('hybrid_switch/circuit_link%d/lu' % (i),
                          'clear', "")
        clickWriteHandler('hybrid_switch/packet_up_link%d/lu' % (i),
                          'clear', "")
        clickWriteHandler('hybrid_switch/ps/packet_link%d/lu' % (i),
                          'clear', "")
    clickWriteHandler('traffic_matrix', 'clear', "")


def divertACKs(divert):
    clickWriteHandler('divert_acks', 'switch', 1 if divert else 0)


def setCircuitLinkDelay(delay):
    for i in xrange(1, NUM_RACKS+1):
        clickWriteHandler('hybrid_switch/circuit_link%d/lu' % (i),
                          'latency', delay)


def setPacketLinkBandwidth(bw):
    for i in xrange(1, NUM_RACKS+1):
        clickWriteHandler('hybrid_switch/packet_up_link%d/lu' % (i),
                          'bandwidth', '%.1fGbps' % bw)
        clickWriteHandler('hybrid_switch/ps/packet_link%d/lu' % (i),
                          'bandwidth', '%.1fGbps' % bw)


def setSolsticeThresh(thresh):
    clickWriteHandler('sol', 'setThresh', thresh)


##
# Scheduling
##
def enableSolstice():
    clickWriteHandler('sol', 'setEnabled', 'true')
    time.sleep(0.1)


def disableSolstice():
    clickWriteHandler('sol', 'setEnabled', 'false')
    time.sleep(0.1)


def disableCircuit():
    disableSolstice()
    off_sched = '1 20000 %s' % (('-1/' * NUM_RACKS)[:-1])
    clickWriteHandler('runner', 'setSchedule', off_sched)
    time.sleep(0.1)


def setStrobeSchedule(reconfig_delay):
    disableSolstice()
    schedule = '%d ' % ((NUM_RACKS-1)*2)
    for i in xrange(NUM_RACKS-1):
        configstr = '%d %s %d %s '
        night_len = reconfig_delay * TDF
        off_config = ('-1/' * NUM_RACKS)[:-1]
        duration = night_len * 9  # night_len * duty_cycle
        configuration = ''
        for j in xrange(NUM_RACKS):
            configuration += '%d/' % ((i + 1 + j) % NUM_RACKS)
        configuration = configuration[:-1]
        schedule += (configstr % (duration, configuration, night_len,
                                  off_config))
    schedule = schedule[:-1]
    clickWriteHandler('runner', 'setSchedule', schedule)
    time.sleep(0.1)


def setCircuitSchedule(configuration):
    disableSolstice()
    schedule = '1 %d %s' % (20 * TDF * 10 * 10, configuration)
    clickWriteHandler('runner', 'setSchedule', schedule)
    time.sleep(0.1)


def setFixedSchedule(schedule):
    disableSolstice()
    clickWriteHandler('runner', 'setSchedule', schedule)
    time.sleep(0.1)


def setConfig(config):
    global CURRENT_CONFIG, FN_FORMAT
    CURRENT_CONFIG = {'type': 'normal', 'buffer_size': 16,
                      'traffic_source': 'QUEUE', 'queue_resize': False,
                      'in_advance': 12000, 'cc': 'reno', 'packet_log': True,
                      'divert_acks': False, 'circuit_link_delay': 0.000600,
                      'packet_link_bandwidth': 10 / 20.0, 'hdfs': False,
                      'thresh': 1000000}
    CURRENT_CONFIG.update(config)
    c = CURRENT_CONFIG
    clearCounters()
    setQueueResize(False)  # let manual queue sizes be passed through first
    setQueueSize(c['buffer_size'])
    setEstimateTrafficSource(c['traffic_source'])
    setQueueResize(c['queue_resize'])
    setInAdvance(c['in_advance'])
    common.setCC(c['cc'])
    setSolsticeThresh(c['thresh'])
    t = c['type']
    if t == 'normal':
        enableSolstice()
    if t == 'no_circuit':
        disableCircuit()
    if t == 'strobe':
        setStrobeSchedule(reconfig_delay=20)
    if t == 'short_reconfig':
        setStrobeSchedule(reconfig_delay=10)
    if t == 'circuit':
        setCircuitSchedule(DEFAULT_CIRCUIT_CONFIG)
    if t == 'fixed':
        setFixedSchedule(c['fixed_schedule'])
    divertACKs(c['divert_acks'])
    setCircuitLinkDelay(c['circuit_link_delay'])
    setPacketLinkBandwidth(c['packet_link_bandwidth'])
    FN_FORMAT = '%s-%s-%s-%d-%s-%s-%s-%s-%s-%s-%s-' % (TIMESTAMP, SCRIPT, t,
                                                       c['buffer_size'],
                                                       c['traffic_source'],
                                                       c['queue_resize'],
                                                       c['in_advance'],
                                                       c['cc'],
                                                       c['circuit_link_delay'],
                                                       c['packet_link_bandwidth'],
                                                       c['hdfs'])
    FN_FORMAT += '%s.txt'
    if config and c['packet_log']:
        setLog('/tmp/' + FN_FORMAT % 'click')
    if not c['packet_log']:
        disableLog()
