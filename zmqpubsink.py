import zmq
import numpy as np
import matplotlib.pyplot as plt
import logging
import sys 
import configparser
import math 
import time
import paho.mqtt.client as mqtt
import datetime
import pmt
from xmlrpc.client import ServerProxy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        #logging.FileHandler("logfile.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

if len(sys.argv) != 3:
	print("Need ini file and output csv e.g: python3 %s SDREventDetector.ini SDREventDetector.csv" % ( sys.argv[0]))
	sys.exit(1)

config = configparser.ConfigParser()

try:
    with open(sys.argv[1]) as f:
        config.read_file(f)
        
        centre_freq = int(config["grc"]["centre_freq"])       
        gain = int(config["grc"]["gain"])                     
        sample_rate = int(config["grc"]["sample_rate"])       
        fft_resolution = int(config["grc"]["fft_resolution"])
        fft_frame_rate = int(config["grc"]["fft_frame_rate"])

        xml_rpc_port = config["rpc-network-config"]["xml_rpc_port"]
        xml_rpc_server = config["rpc-network-config"]["xml_rpc_server"]
        xml_rpc_address = "http://" + xml_rpc_server + ":" + xml_rpc_port
        zmq_address = config["zmq-network-config"]["zmq_address"]     
        
        seconds_to_buffer = int(config["client"]["seconds_to_buffer"])
        trigger_gain_threshold = float(config["client"]["trigger_gain_threshold"])
        
        if config.has_section("mqtt"):
            mqtt_ip_address = config["mqtt"]["mqtt_ip_address"] 
            mqtt_username = config["mqtt"]["mqtt_username"]
            mqtt_password = config["mqtt"]["mqtt_password"]
            mqtt_topic = config["mqtt"]["mqtt_topic"]
            mqtt_client = mqtt.Client() 
            mqtt_client.username_pw_set(mqtt_username, mqtt_password)
            try:
                mqtt_client.connect(mqtt_ip_address, 1883)
            except:
                logging.warning("Cannot connect to MQTT check config file and server")
            mqtt_client.loop_start()
except IOError:
    logging.error("No config file called %s present, exiting", sys.argv[1])
    raise SystemExit

logging.info("Started")

csv_file = open(sys.argv[2], 'a')

frequency_range_per_fft_bin = int((sample_rate / 2) / (fft_resolution / 2))

bin_frequency_values=[]
for index in range(0, fft_resolution):
    bin_frequency_values.append(centre_freq + (frequency_range_per_fft_bin*(index - (fft_resolution/2))))

zmq_pub_sink_context = zmq.Context()
zmq_pub_sink = zmq_pub_sink_context.socket(zmq.SUB)
zmq_pub_sink.connect(zmq_address)
zmq_pub_sink.setsockopt(zmq.SUBSCRIBE, b'')

#   With this cab retune and reconfigure radio on the fly
#   
#   xmlrpc_endpoint = ServerProxy(xml_rpc_address)
#   
#   xmlrpc_endpoint.set_center_freq(centre_freq)
#   xmlrpc_endpoint.set_gain(gain)
#   xmlrpc_endpoint.set_sample_rate(sample_rate) 
#   xmlrpc_endpoint.set_fft_resolution(fft_resolution) 
#   xmlrpc_endpoint.set_fft_frame_rate(fft_frame_rate) 

fft_data_history = []

while True:

    start_time = time.time()

    if zmq_pub_sink.poll(10) != 0:
        msg = zmq_pub_sink.recv()
        message_size = len(msg)
        data = np.frombuffer(msg, dtype=np.float32, count=fft_resolution)
        fft_data = data[0:fft_resolution]

        fft_data_history.append(fft_data)
        fft_data_history_as_np = np.asarray(fft_data_history)
        fft_data_history_mean = fft_data_history_as_np.mean(axis=0)

        if len(fft_data_history) == (fft_frame_rate * seconds_to_buffer) + 1: 
            del(fft_data_history[0])
            for index,value in enumerate(fft_data):              
                average_power_in_band = fft_data_history_mean[index]
                if (fft_data[index] > (average_power_in_band + trigger_gain_threshold)):
                    event_frequency = bin_frequency_values[index]
                    event_power = fft_data[index]
                    now = datetime.datetime.now()
                    snr = fft_data[index] - average_power_in_band
                    csv_entry="%s,%d,%0.2f,%0.2f\n" % (time.time(),event_frequency,event_power,snr)
                    csv_file.write(csv_entry)
                    csv_file.flush()
                    logging.info(csv_entry)
                    if config.has_section("mqtt"):
                         mqtt_client.publish(mqtt_topic, csv_entry)
           
    end_time = time.time()
    delta_time = end_time - start_time
    delta_time_target = 1.0/float(fft_frame_rate)
    if(delta_time > delta_time_target):
       logging.warning("Not real time: execution in %.3f not %.3f seconds, reduce fft_resolution and/or fft_frame_rate", delta_time, delta_time_target)                            
                    

        