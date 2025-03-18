import sys
import logging
import datetime
import logging
import numpy as np
import pandas as pd
from plotnine import *
from mizani.formatters import date_format
import os

logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.INFO)

if len(sys.argv) != 3:
	print("Need csv file and snr_above_threshold_cutoff e.g: python3 %s SDREventDetector.csv 0.0" % ( sys.argv[0]))
	sys.exit(1)

csvfile = sys.argv[1]
colnames = ['timestamp-utc','frequency','power','snr_above_threshold']
logging.info("Processing %s", csvfile)

event_df = pd.read_csv(csvfile, names=colnames, header=None).dropna()

event_df['timestamp-utc'] = event_df['timestamp-utc'].apply(lambda x: datetime.datetime.fromtimestamp(x))

snr_above_threshold_cutoff = float(sys.argv[2])

event_df = event_df[event_df['snr_above_threshold'] > snr_above_threshold_cutoff]

title = "Events by frequency"

event_df_expanded_1 = event_df[['timestamp-utc','frequency','snr_above_threshold']] 
event_df_expanded_2 = event_df[['timestamp-utc','frequency','snr_above_threshold']]
event_df_expanded = pd.concat([event_df_expanded_1, event_df_expanded_2])

event_df_expanded['publishedAt'] = pd.to_datetime(event_df_expanded['timestamp-utc'])
event_df_expanded = event_df_expanded.set_index(['publishedAt'])
event_df_expanded = event_df_expanded.last('24h')

graph = ggplot(event_df_expanded, 
        aes(y = 'timestamp-utc', x = 'frequency')) + geom_point(aes(size='snr_above_threshold') , alpha=0.05) + \
        ylab("Hour") + labs(x = "Frequency") + theme(axis_text_x=element_text(rotation=90, size=6)) + \
        scale_y_datetime(date_breaks = "1 hour", labels = date_format("%H")) + \
        theme(axis_text_y=element_text(size=6)) + theme(figure_size=(16, 8)) + \
        ggtitle(title)

plot_filename = os.getcwd() + '/events-by-frequency.jpg'
logging.info("Saving %s", plot_filename)
graph.save(filename = plot_filename, dpi = 600)

title = "Events by time of day"

event_df['timestamp-utc-copy'] = event_df['timestamp-utc']
event_df['timestamp-utc-copy'] = event_df['timestamp-utc-copy'].apply(lambda dt: dt.replace(hour=0,minute=0,second=0))
event_df['timestamp-utc'] = event_df['timestamp-utc'].apply(lambda dt: dt.replace(day=1,month=1,year=2000))

graph = ggplot(event_df, aes(y = 'timestamp-utc', x = 'timestamp-utc-copy')) + geom_point(aes(size='snr_above_threshold'), alpha=0.05) + \
        ylab("Hour") + theme(axis_text_x=element_text(rotation=90, size=6)) + \
        xlab("Day") + theme(axis_text_x=element_text(size=6)) + \
        scale_y_datetime(date_breaks = "1 hour", labels = date_format("%H")) + \
        scale_x_datetime(date_breaks = "1 day", labels = date_format("%d/%m/%Y")) + \
        theme(axis_text_y=element_text(size=6)) + theme(figure_size=(16, 8)) + \
        ggtitle(title)

plot_filename = os.getcwd() + '/events-by-timeofday.jpg'
logging.info("Saving %s", plot_filename)
graph.save(filename = plot_filename, dpi = 600)







