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

zmq_endpoint="tcp://127.0.0.1:50242"
zmq_push_endpoint="tcp://127.0.0.1:50241"

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
        
        seconds_to_buffer = int(config["client"]["seconds_to_buffer"])
        fft_supersample = 2 ** int(config["client"]["fft_supersample"])
        trigger_gain_threshold = float(config["client"]["trigger_gain_threshold"])

        if fft_supersample >= fft_resolution:
            logging.critical("fft_supersample needs to be less than %d as fft_resolution is %d. Why not try 1 instead and work up to see what works best for you?",
                                    math.log2(fft_resolution), fft_resolution)
            sys.exit()
        
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
start_bin = 0
end_bin = fft_resolution
rebinned_fft_size = int(fft_resolution / fft_supersample)

rebinned_frequency_values=[]
for index in range(0, rebinned_fft_size):
    rebinned_frequency_values.append(int((centre_freq - (int(sample_rate/2))) + ((index + 1) * frequency_range_per_fft_bin * fft_supersample) - 
                                         ((frequency_range_per_fft_bin * fft_supersample)/ 2)))

zmq_pub_sink_context = zmq.Context()
zmq_pub_sink = zmq_pub_sink_context.socket(zmq.SUB)
zmq_pub_sink.connect(zmq_endpoint)
zmq_pub_sink.setsockopt(zmq.SUBSCRIBE, b'')

zmq_push_message_sink_context = zmq.Context()
zmq_push_message_sink = zmq_push_message_sink_context.socket (zmq.PUSH)
zmq_push_message_sink.bind (zmq_push_endpoint)


#https://www.gnuradio.org/doc/sphinx-3.7.0/pmt/dictionary.html
#https://wiki.gnuradio.org/index.php/Message_Passing
#https://www.gnuradio.org/doc/sphinx-3.7.0/pmt/index.html
#https://lists.nongnu.org/archive/html/discuss-gnuradio/2016-12/msg00108.html

# cmd port, want dict gain = float.
pmt_dict = pmt.make_dict()
pmt.dict_add(pmt_dict, pmt.intern('gain'), pmt.to_pmt(10))
zmq_push_message_sink.send(pmt.serialize_str((pmt.cons(pmt.intern("cmd"), pmt_dict))))         

fft_data_rebinned_max_history = [np.array([]) for _ in range(rebinned_fft_size)]

while True:

    start_time = time.time()

    if zmq_pub_sink.poll(10) != 0:
        msg = zmq_pub_sink.recv()
        message_size = len(msg)
        data = np.frombuffer(msg, dtype=np.float32, count=fft_resolution)
        fft_data = data[start_bin:end_bin]
        fft_data_rebinned = np.split(fft_data, rebinned_fft_size, axis=0)
        fft_data_rebinned_max = [np.max(subarray) for subarray in fft_data_rebinned]
        fft_data_rebinned_argmax = [np.argmax(subarray) for subarray in fft_data_rebinned]
        end_event_frequency = 0
        end_event_power = 0
        for index,value in enumerate(fft_data_rebinned_max):
            fft_data_rebinned_max_history[index] = np.append(fft_data_rebinned_max_history[index], fft_data_rebinned_max[index])
            if len(fft_data_rebinned_max_history[index]) == (fft_frame_rate * seconds_to_buffer) + 1: 
                fft_data_rebinned_max_history[index] = np.delete(fft_data_rebinned_max_history[index], 0)
                average_power_in_band = np.average(fft_data_rebinned_max_history[index])
                if (fft_data_rebinned_max[index] > (average_power_in_band + trigger_gain_threshold)):
                    event_frequency = rebinned_frequency_values[index]
                    event_power = fft_data_rebinned_max[index]
                    now = datetime.datetime.now()
                    csv_entry="%s,%d,%d\n" % (now.strftime("%d-%m-%Y %H:%M:%S.%f"),event_frequency, event_power)
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
                    

        