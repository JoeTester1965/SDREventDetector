#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: SDREventDetector-grc
# Author: JoeTester1965
# Copyright: MIT License
# GNU Radio version: 3.10.5.1

from gnuradio import blocks
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import soapy
from gnuradio import zeromq
from gnuradio.fft import logpwrfft
from xmlrpc.server import SimpleXMLRPCServer
import threading
import configparser




class SDREventDetector(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "SDREventDetector-grc", catch_exceptions=True)

        ##################################################
        # Variables
        ##################################################
        self._zmq_network_config_config = configparser.ConfigParser()
        self._zmq_network_config_config.read('SDREventDetector.ini')
        try: zmq_network_config = self._zmq_network_config_config.get('zmq-network-config', 'zmq_address')
        except: zmq_network_config = 'tcp://127.0.0.1:50242'
        self.zmq_network_config = zmq_network_config
        self._xml_rpc_server_config = configparser.ConfigParser()
        self._xml_rpc_server_config.read('SDREventDetector.ini')
        try: xml_rpc_server = self._xml_rpc_server_config.get('rpc-network-config', xml_rpc_server)
        except: xml_rpc_server = "127.0.0.1"
        self.xml_rpc_server = xml_rpc_server
        self._xml_rpc_port_config = configparser.ConfigParser()
        self._xml_rpc_port_config.read('SDREventDetector.ini')
        try: xml_rpc_port = self._xml_rpc_port_config.getint('rpc-network-config', 'xml_rpc_port')
        except: xml_rpc_port = 50249
        self.xml_rpc_port = xml_rpc_port
        self._sample_rate_config = configparser.ConfigParser()
        self._sample_rate_config.read('SDREventDetector.ini')
        try: sample_rate = self._sample_rate_config.getint('grc', 'sample_rate')
        except: sample_rate = 2048000
        self.sample_rate = sample_rate
        self._gain_config = configparser.ConfigParser()
        self._gain_config.read('SDREventDetector.ini')
        try: gain = self._gain_config.getint('grc', 'gain')
        except: gain = 10
        self.gain = gain
        self._fft_resolution_config = configparser.ConfigParser()
        self._fft_resolution_config.read('SDREventDetector.ini')
        try: fft_resolution = self._fft_resolution_config.getint('grc', 'fft_resolution')
        except: fft_resolution = 20
        self.fft_resolution = fft_resolution
        self._fft_frame_rate_config = configparser.ConfigParser()
        self._fft_frame_rate_config.read('SDREventDetector.ini')
        try: fft_frame_rate = self._fft_frame_rate_config.getint('grc', 'fft_frame_rate')
        except: fft_frame_rate = 1024
        self.fft_frame_rate = fft_frame_rate
        self._center_freq_config = configparser.ConfigParser()
        self._center_freq_config.read('SDREventDetector.ini')
        try: center_freq = self._center_freq_config.getint('grc', 'center_freq')
        except: center_freq = 434000000
        self.center_freq = center_freq

        ##################################################
        # Blocks
        ##################################################

        self.zeromq_pub_sink_0 = zeromq.pub_sink(gr.sizeof_float, fft_resolution, zmq_network_config, 100, False, (-1), '', True)
        self.xmlrpc_server_0 = SimpleXMLRPCServer((xml_rpc_server, xml_rpc_port), allow_none=True)
        self.xmlrpc_server_0.register_instance(self)
        self.xmlrpc_server_0_thread = threading.Thread(target=self.xmlrpc_server_0.serve_forever)
        self.xmlrpc_server_0_thread.daemon = True
        self.xmlrpc_server_0_thread.start()
        self.soapy_rtlsdr_source_0 = None
        dev = 'driver=rtlsdr'
        stream_args = ''
        tune_args = ['']
        settings = ['']

        self.soapy_rtlsdr_source_0 = soapy.source(dev, "fc32", 1, '',
                                  stream_args, tune_args, settings)
        self.soapy_rtlsdr_source_0.set_sample_rate(0, sample_rate)
        self.soapy_rtlsdr_source_0.set_gain_mode(0, False)
        self.soapy_rtlsdr_source_0.set_frequency(0, center_freq)
        self.soapy_rtlsdr_source_0.set_frequency_correction(0, 0)
        self.soapy_rtlsdr_source_0.set_gain(0, 'TUNER', gain)
        self.logpwrfft_x_0 = logpwrfft.logpwrfft_c(
            sample_rate=sample_rate,
            fft_size=fft_resolution,
            ref_scale=1,
            frame_rate=fft_frame_rate,
            avg_alpha=1.0,
            average=True,
            shift=True)
        self.blocks_correctiq_0 = blocks.correctiq()


        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_correctiq_0, 0), (self.logpwrfft_x_0, 0))
        self.connect((self.logpwrfft_x_0, 0), (self.zeromq_pub_sink_0, 0))
        self.connect((self.soapy_rtlsdr_source_0, 0), (self.blocks_correctiq_0, 0))


    def get_zmq_network_config(self):
        return self.zmq_network_config

    def set_zmq_network_config(self, zmq_network_config):
        self.zmq_network_config = zmq_network_config

    def get_xml_rpc_server(self):
        return self.xml_rpc_server

    def set_xml_rpc_server(self, xml_rpc_server):
        self.xml_rpc_server = xml_rpc_server
        self._xml_rpc_server_config = configparser.ConfigParser()
        self._xml_rpc_server_config.read('SDREventDetector.ini')
        if not self._xml_rpc_server_config.has_section('rpc-network-config'):
        	self._xml_rpc_server_config.add_section('rpc-network-config')
        self._xml_rpc_server_config.set('rpc-network-config', self.xml_rpc_server, str(None))
        self._xml_rpc_server_config.write(open('SDREventDetector.ini', 'w'))

    def get_xml_rpc_port(self):
        return self.xml_rpc_port

    def set_xml_rpc_port(self, xml_rpc_port):
        self.xml_rpc_port = xml_rpc_port

    def get_sample_rate(self):
        return self.sample_rate

    def set_sample_rate(self, sample_rate):
        self.sample_rate = sample_rate
        self.logpwrfft_x_0.set_sample_rate(self.sample_rate)
        self.soapy_rtlsdr_source_0.set_sample_rate(0, self.sample_rate)

    def get_gain(self):
        return self.gain

    def set_gain(self, gain):
        self.gain = gain
        self.soapy_rtlsdr_source_0.set_gain(0, 'TUNER', self.gain)

    def get_fft_resolution(self):
        return self.fft_resolution

    def set_fft_resolution(self, fft_resolution):
        self.fft_resolution = fft_resolution

    def get_fft_frame_rate(self):
        return self.fft_frame_rate

    def set_fft_frame_rate(self, fft_frame_rate):
        self.fft_frame_rate = fft_frame_rate

    def get_center_freq(self):
        return self.center_freq

    def set_center_freq(self, center_freq):
        self.center_freq = center_freq
        self.soapy_rtlsdr_source_0.set_frequency(0, self.center_freq)




def main(top_block_cls=SDREventDetector, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    tb.wait()


if __name__ == '__main__':
    main()
