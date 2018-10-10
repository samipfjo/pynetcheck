"""
File          :: netcheck.py
Description   :: A tool for automated ping and speedtest scheduling, configurable via source code.
Project Home  :: https://github.com/luketimothyjones/pynetcheck
License       :: MIT + attribution (maintaining this header block is plenty)
Contributors  :: Luke Pflibsen-Jones [GH: luketimothyjones] (author)
                 
"""

import csv
import os
import re
import sqlite3
import subprocess
import sys
import time

import arrow
import speedtest


# ------
DELAY_MINUTES = 10

TIMEZONE = 'US/Pacific'
TIMESTAMP_FORMAT = 'YY/MM/DD HH:mm'

PING_DESTINATION = 'www.google.com'
PING_QUANTITY = 25


# ------
percent_lost_re = re.compile('([0-9]{1,3})% loss')
min_ms_re = re.compile('Minimum = ([0-9]+)')
max_ms_re = re.compile('Maximum = ([0-9]+)')
average_ms_re = re.compile('Average = ([0-9]+)')

database_connection = sqlite3.connect('connection_data.sqlite')


def maybe_create_tables():
    """
    Creates database tables if they do not already exist
    """

    pings = \
'''CREATE TABLE `pings` (
	`date`	VARCHAR(20),
	`percent_lost`	INTEGER,
	`packets_sent`	INTEGER,
	`min_ms`	INTEGER,
	`max_ms`	INTEGER,
	`average_ms`	INTEGER,
	PRIMARY KEY(date)
);'''

    speedtests = \
'''CREATE TABLE `speedtests` (
	`date`	VARCHAR(20),
	`ping`	INTEGER,
	`download_mbps`	FLOAT,
	`upload_mbps`	FLOAT,
	`server`	VARCHAR(100),
	PRIMARY KEY(date)
);'''

    pings_checker = "SELECT name FROM sqlite_master WHERE type='table' AND name='pings';"
    speedtests_checker = "SELECT name FROM sqlite_master WHERE type='table' AND name='speedtests';"

    # Make sure the tables exist in the database
    with database_connection:
        if database_connection.execute(pings_checker).fetchone() is None and \
           database_connection.execute(speedtests_checker).fetchone() is None:
            database_connection.execute(pings)
            database_connection.execute(speedtests)

# ------
def consprint(string='', end='\n'):
    sys.stdout.write(string + end)
    sys.stdout.flush()

# ------
def ping_speedtest_save():
    consprint('Running pings...', end='')

    datetime = arrow.now(TIMEZONE).format(TIMESTAMP_FORMAT)
    data = str(subprocess.Popen(['ping', PING_DESTINATION, '-n', str(PING_QUANTITY)], stdout=subprocess.PIPE).stdout.read())[2:-1]

    # Extract data from ping results
    percent_lost = percent_lost_re.search(data).group(1)
    min_ms = min_ms_re.search(data).group(1)
    max_ms = max_ms_re.search(data).group(1)
    average_ms = average_ms_re.search(data).group(1)

    # ---
    consprint('\rRunning speedtest...', end='')

    sptest = speedtest.Speedtest()
    sptest.get_best_server()

    speedtest_ping = int(sptest.results.ping)
    speedtest_dl_mbps = round(sptest.download() / 1000000, 2)  # Convert from bits/s to megabits/s
    speedtest_up_mbps = round(sptest.upload() / 1000000, 2)

    speedtest_server = f'{sptest.results.server["sponsor"]} ({sptest.results.server["name"]})'

    consprint(f'\r{datetime}   {percent_lost:<7}{min_ms:<7}{max_ms:<7}{average_ms:<7}|    '
              f'{speedtest_ping:<7}{"{:.2f}".format(speedtest_dl_mbps):<11}{"{:.2f}".format(speedtest_up_mbps):<11}{speedtest_server}')

    # ---
    # Save results to database
    with database_connection:
        database_connection.execute(
            'INSERT INTO pings(date, percent_lost, packets_sent, min_ms, max_ms, average_ms) VALUES (?, ?, ?, ?, ?, ?)',
            (datetime, percent_lost, PING_QUANTITY, min_ms, max_ms, average_ms))

        database_connection.execute(
            'INSERT INTO speedtests(date, ping, download_mbps, upload_mbps, server) VALUES (?, ?, ?, ?, ?)',
            (datetime, speedtest_ping, speedtest_dl_mbps, speedtest_up_mbps, speedtest_server))

# ------
def dump_data_to_csv():
    csv.register_dialect('pretty', delimiter='\t', quoting=csv.QUOTE_NONE)

    with database_connection:
        with open('pings.csv', 'w', newline='') as ping_file:
            print('\t'.join('Date/time Percent_Lost Packets_Sent Min Max Avg'.split()), file=ping_file)

            ping_writer = csv.writer(ping_file, dialect='pretty')
            ping_data = database_connection.execute('SELECT * FROM pings').fetchall()
            ping_writer.writerows(ping_data)

        with open('pings.csv', 'w', newline='') as speedtest_file:
            print('\t'.join('Date/time Ping Download Upload Server'.split()), file=speedtest_file)

            speedtest_writer = csv.writer(speedtest_file, dialect='pretty')
            speedtest_data = database_connection.execute('SELECT * FROM speedtests').fetchall()
            speedtest_writer.writerows(speedtest_data)

# ------
def main():
    maybe_create_tables()

    consprint('Date/time        Lost   Min    Max    Avg    |    Ping   Download   Upload     Server')
    while 1:
        ping_speedtest_save()
        time.sleep(DELAY_MINUTES * 60)

# ------
if __name__ == '__main__':
    try:
        main()

    except KeyboardInterrupt:
        consprint('\nDumping most recent data to CSVs...')
        dump_data_to_csv()
        consprint()
