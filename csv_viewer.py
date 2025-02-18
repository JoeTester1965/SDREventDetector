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

csvfile = "SDREventDetector.csv"
colnames = ['timestamp','timestamp-utc','start_freq','start_power','end_freq','end_power','bins']
logging.info("Processing %s", csvfile)

event_df = pd.read_csv(csvfile, names=colnames, header=None).dropna()

event_df['timestamp-utc'] = event_df['timestamp-utc'].apply(lambda x: datetime.datetime.fromtimestamp(x))

title = "Events by frequency"

event_df_expanded_1 = event_df[['timestamp-utc','start_freq','start_power']] 
event_df_expanded_1.rename(columns={"start_freq": "freq", "start_power": "power"}, inplace=True)
event_df_expanded_2 = event_df[['timestamp-utc','end_freq','end_power']]
event_df_expanded_2.rename(columns={"end_freq": "freq", "end_power": "power"}, inplace=True)
event_df_expanded = pd.concat([event_df_expanded_1, event_df_expanded_2])

event_df_expanded['publishedAt'] = pd.to_datetime(event_df_expanded['timestamp-utc'])
event_df_expanded = event_df_expanded.set_index(['publishedAt'])
event_df_expanded = event_df_expanded.last('24h')

graph = ggplot(event_df_expanded, 
        aes(y = 'timestamp-utc', x = 'freq')) + geom_point(aes(size='power') , alpha=0.05) + \
        ylab("Hour") + labs(x = "Frequency") + theme(axis_text_x=element_text(rotation=90, size=6)) + \
        scale_x_continuous(breaks = [0,10000,20000,30000,40000,50000,60000,70000,80000,90000,100000,110000,120000,130000,140000,150000]) + \
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

graph = ggplot(event_df, aes(y = 'timestamp-utc', x = 'timestamp-utc-copy')) + geom_point(aes(size='start_power'), alpha=0.05) + \
        ylab("Hour") + theme(axis_text_x=element_text(rotation=90, size=6)) + \
        xlab("Day") + theme(axis_text_x=element_text(size=6)) + \
        scale_y_datetime(date_breaks = "1 hour", labels = date_format("%H")) + \
        scale_x_datetime(date_breaks = "1 day", labels = date_format("%d/%m/%Y")) + \
        theme(axis_text_y=element_text(size=6)) + theme(figure_size=(16, 8)) + \
        ggtitle(title)

plot_filename = os.getcwd() + '/events-by-timeofday.jpg'
logging.info("Saving %s", plot_filename)
graph.save(filename = plot_filename, dpi = 600)







