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

expected_config_file = "SDREventDetector.ini"
output_csv_file = "SDREventDetector.csv"
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

config = configparser.ConfigParser()

try:
    with open(expected_config_file) as f:
        config.read_file(f)
        samp_rate = int(config["graph"]["sample_rate"])
        centre_freq = int(config["graph"]["centre_freq"])
        fft_resolution = int(config["graph"]["fft_resolution"])
        fft_frame_rate = int(config["graph"]["fft_frame_rate"])
        start_freq = int(config["client"]["start_freq"])
        end_freq = int(config["client"]["end_freq"])
        freq_bin_range = int(config["client"]["freq_bin_range"])
        trigger_gain_threshold = float(config["client"]["trigger_gain_threshold"])
        trigger_abs_threshold = float(config["client"]["trigger_abs_threshold"])
        bin_count_threshold = int(config["client"]["bin_count_threshold"])
        retrigger_seconds = int(config["client"]["retrigger_seconds"])
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
    logging.error("No config file called %s present, exiting", expected_config_file)
    raise SystemExit

logging.info("Started")

csv_file = open(output_csv_file, 'a')

frequency_range_per_fft_bin = (samp_rate / 2) / (fft_resolution / 2)
start_bin = math.floor((start_freq / frequency_range_per_fft_bin) + (fft_resolution / 2))
end_bin = math.floor((end_freq / frequency_range_per_fft_bin) + (fft_resolution / 2))
rebinned_fft_size = math.floor((end_freq - start_freq) / freq_bin_range)
num_bins = end_bin - start_bin
end_bin = end_bin + (rebinned_fft_size - (num_bins % rebinned_fft_size))

rebinned_frequency_values=[]
for index in range(0, rebinned_fft_size):
    rebinned_frequency_values.append(start_freq + ((index + 1) * freq_bin_range) - (freq_bin_range / 2))

bins_to_merge = math.floor(freq_bin_range / frequency_range_per_fft_bin)

zmq_pub_sink_context = zmq.Context()
zmq_pub_sink = zmq_pub_sink_context.socket(zmq.SUB)
zmq_pub_sink.connect(zmq_endpoint)
zmq_pub_sink.setsockopt(zmq.SUBSCRIBE, b'')

zmq_push_message_sink_context = zmq.Context()
zmq_push_message_sink = zmq_push_message_sink_context.socket (zmq.PUSH)
zmq_push_message_sink.bind (zmq_push_endpoint)

bat_data_rebinned_max_history = [np.array([]) for _ in range(rebinned_fft_size)]
last_trigger_time = []
last_trigger_time = [time.time() for i in range(rebinned_fft_size)] 

while True:
    if zmq_pub_sink.poll(10) != 0:
        msg = zmq_pub_sink.recv()
        message_size = len(msg)
        data = np.frombuffer(msg, dtype=np.float32, count=fft_resolution)
        bat_data = data[start_bin:end_bin]
        bat_data_rebinned = np.split(bat_data, rebinned_fft_size, axis=0)
        bat_data_rebinned_max = [np.max(subarray) for subarray in bat_data_rebinned]
        bat_data_rebinned_argmax = [np.argmax(subarray) for subarray in bat_data_rebinned]
        bin_count = 0
        start_event_frequency = 0
        start_event_power = 0
        end_event_frequency = 0
        end_event_power = 0
        tuning_frequency = 0
        for index,value in enumerate(bat_data_rebinned_max):
            bat_data_rebinned_max_history[index] = np.append(bat_data_rebinned_max_history[index], bat_data_rebinned_max[index])
            if len(bat_data_rebinned_max_history[index]) == (fft_frame_rate * retrigger_seconds) + 1: 
                bat_data_rebinned_max_history[index] = np.delete(bat_data_rebinned_max_history[index], 0)
                average_power_in_band = np.average(bat_data_rebinned_max_history[index])
                if (bat_data_rebinned_max[index] > (average_power_in_band + trigger_gain_threshold)) and (bat_data_rebinned_max[index] > trigger_abs_threshold):
                    event_frequency = rebinned_frequency_values[index] + (frequency_range_per_fft_bin * bat_data_rebinned_argmax[index])
                    if start_event_frequency == 0:
                        start_event_frequency = event_frequency
                        start_event_power = bat_data_rebinned_max[index]
                        if event_frequency < (samp_rate / decimation / 2):
                            tuning_frequency = 0
                        else:
                            tuning_frequency = event_frequency - (samp_rate / decimation / 2)
                    else:
                        end_event_frequency = event_frequency
                        end_event_power = bat_data_rebinned_max[index]
                    bin_count = bin_count + 1
        if bin_count >= bin_count_threshold:
            if  (time.time() - last_trigger_time[index]) > retrigger_seconds:
                last_trigger_time[index] = time.time()
                zmq_push_message_sink.send(pmt.serialize_str((pmt.cons(pmt.intern("freq"), pmt.to_pmt(float(tuning_frequency))))))
                now = datetime.datetime.now()
                csv_entry="%s,%s,%0.0f,%d,%0.0f,%d,%d\n" % (now.strftime("%Y-%m-%d %H:%M:%S"),time.time(),
                                                            start_event_frequency, start_event_power, end_event_frequency, end_event_power, bin_count)
                csv_file.write(csv_entry)
                csv_file.flush()
                logging.info(csv_entry)
                if config.has_section("mqtt"):
                    mqtt_client.publish(mqtt_topic, csv_entry)
                                
                    

        