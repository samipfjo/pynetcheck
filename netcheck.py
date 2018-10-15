"""
File          :: netcheck.py
Description   :: A tool for automated ping and speedtest scheduling, configurable via source code.
Project Home  :: https://github.com/luketimothyjones/pynetcheck
License       :: MIT + attribution (maintaining this header block is plenty)
Contributors  :: Luke Pflibsen-Jones [GH: luketimothyjones] (author)
              :: Joseph Redfern [GH: JosephRedfern]  (cross-platform support, conversion into class, basic CLI)
"""

import csv
import re
import sqlite3
import subprocess
import sys
import time

import arrow
import speedtest


class PyNetCheck:

    def __init__(self, ping_count, ping_host, test_delay, db_filename, timezone, timestamp_format, _test_platform=None):
        """
        Interface for automated ping and throughput (speed) tests.
        See command line options for usage.
        """

        self.ping_count = ping_count
        self.ping_host = ping_host
        self.test_delay = test_delay
        self.db = sqlite3.connect(db_filename)
        self.timezone = timezone
        self.timestamp_format = timestamp_format

        if (_test_platform is None and sys.platform in ('linux', 'cygwin', 'darwin')) or _test_platform in ('linux', 'cygwin', 'darwin'):
            self.percent_lost_re = re.compile(r'(?P<percent_lost>\d*[.,]?\d*)% (\w+ ?){1,2}')
            self.min_max_avg_re = re.compile(r'\w+/\w+/\w+/\w+ = (?P<min>\d*[.,]?\d*)/(?P<avg>\d*[.,]?\d*)/(?P<max>\d*[.,]?\d*)')

        elif (_test_platform is None and sys.platform == 'win32') or _test_platform == 'win32':
            self.percent_lost_re = re.compile(r'(?P<percent_lost>\d{1,3})% (\w+ ?){1,2}')
            self.min_max_avg_re = re.compile(r'\w+ = (?P<min>\d+)ms, \w+ = (?P<max>\d+)ms, \w+ = (?P<avg>\d+)ms')

        else:
            raise Exception('Unsupported Platform.')

    # ----
    def maybe_create_tables(self):
        """
        Creates database tables if they do not already exist
        """

        pings = '''
        CREATE TABLE IF NOT EXISTS `pings` (
        `date`	VARCHAR(20),
        `percent_lost`	INTEGER,
        `packets_sent`	INTEGER,
        `min_ms`	INTEGER,
        `max_ms`	INTEGER,
        `average_ms`	INTEGER,
        PRIMARY KEY(date));
        '''

        speedtests = '''
        CREATE TABLE IF NOT EXISTS `speedtests` (
        `date`	VARCHAR(20),
        `ping`	INTEGER,
        `download_mbps`	FLOAT,
        `upload_mbps`	FLOAT,
        `server`	VARCHAR(100),
        PRIMARY KEY(date));
        '''

        self.db.execute(pings)
        self.db.execute(speedtests)

    # ----
    def consprint(self, string='', end='\n'):
        """
        Helper method to print to console, allowing previous line to be over-written.
        """

        sys.stdout.write(string + end)
        sys.stdout.flush()

    # ----
    def ping_speedtest_save(self, _test_ping_data=None):
        """
        Run single ping test, speed test, and write results to DB.
        """

        self.consprint('Running pings...', end='')

        datetime = arrow.now(self.timezone).format(self.timestamp_format)

        percent_lost, min_ms, average_ms, max_ms = self.execute_ping(_test_data=_test_ping_data)

        self.consprint('\rRunning speedtest...', end='')

        sptest = speedtest.Speedtest()
        sptest.get_best_server()

        speedtest_ping = int(sptest.results.ping)
        speedtest_dl_mbps = round(sptest.download() / 1000000, 2)  # Convert from bits/s to megabits/s
        speedtest_up_mbps = round(sptest.upload() / 1000000, 2)

        speedtest_server = f'{sptest.results.server["sponsor"]} ({sptest.results.server["name"]})'

        self.consprint(f'\r{datetime}   {percent_lost:<7}{min_ms:<7}{max_ms:<7}{average_ms:<7}|    '
                       f'{speedtest_ping:<7}{"{:.2f}".format(speedtest_dl_mbps):<11}{"{:.2f}".format(speedtest_up_mbps):<11}{speedtest_server}')

        # Save results to database
        with self.db:
            self.db.execute("""
                            INSERT INTO pings(date, percent_lost, packets_sent, min_ms, max_ms, average_ms)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (datetime, percent_lost, self.ping_count, min_ms, max_ms, average_ms))

            self.db.execute("""
                            INSERT INTO speedtests(date, ping, download_mbps, upload_mbps, server)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (datetime, speedtest_ping, speedtest_dl_mbps, speedtest_up_mbps, speedtest_server))

    # ----
    def execute_ping(self, host=None, count=None, _test_data=None):
        """
        Cross-platform ping implementation. Only tested under linux, but should be
        functional under macOS and Cygwin as AFAIK their outputs are the same...
        """

        host = host or self.ping_host
        count = count or self.ping_count

        if _test_data is not None:
            data = _test_data

        elif sys.platform in ('linux', 'cygwin', 'darwin'):
            data = str(subprocess.Popen(['ping', host, '-c', str(count)], stdout=subprocess.PIPE).stdout.read())

        elif sys.platform == 'win32':
            data = str(subprocess.Popen(['ping', host, '-n', str(count)], stdout=subprocess.PIPE).stdout.read())

        else:
            raise Exception('Unsupported Platform.')

        percent_lost_match = self.percent_lost_re.search(data)
        timing_match = self.min_max_avg_re.search(data)

        percent_lost = int(round(float(percent_lost_match.group('percent_lost'))))
        min_ms = int(round(float(timing_match.group('min'))))
        average_ms = int(round(float(timing_match.group('avg'))))
        max_ms = int(round(float(timing_match.group('max'))))

        return percent_lost, min_ms, average_ms, max_ms

    # ----
    def dump_data_to_csv(self):
        csv.register_dialect('pretty', delimiter='\t', quoting=csv.QUOTE_NONE)

        with self.db:
            with open('pings.csv', 'w', newline='') as ping_file:
                print('\t'.join('Date/time Percent_Lost Packets_Sent Min Max Avg'.split()), file=ping_file)

                ping_writer = csv.writer(ping_file, dialect='pretty')
                ping_data = self.db.execute('SELECT * FROM pings').fetchall()
                ping_writer.writerows(ping_data)

            with open('speedtests.csv', 'w', newline='') as speedtest_file:
                print('\t'.join('Date/time Ping Download Upload Server'.split()), file=speedtest_file)

                speedtest_writer = csv.writer(speedtest_file, dialect='pretty')
                speedtest_data = self.db.execute('SELECT * FROM speedtests').fetchall()
                speedtest_writer.writerows(speedtest_data)

    # ----
    def loop(self):
        """
        Create tables (if needed), and start running the test loop.
        """

        self.maybe_create_tables()
        self.consprint('Date/time           Lost   Min    Max    Avg    |    Ping   Download   Upload     Server')

        while True:
            self.ping_speedtest_save()
            time.sleep(self.test_delay * 60)

    # ----
    def run_once(self, _test_ping_data=None):
        """
        Runs the ping/speedtest once rather than in a print loop.
        For use with external task schedulers.
        """

        self.maybe_create_tables()
        self.ping_speedtest_save(_test_ping_data=_test_ping_data)


# --------
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Check connection latency speed!',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--ping-host', type=str, default='www.google.com', help='Hostname or ip to ping')
    parser.add_argument('--db-filename', type=str, default='connection_data.sqlite', help='Database filename')
    parser.add_argument('--ping-count', type=int, default=25, help='Number of pings to perform during each test')
    parser.add_argument('--test-delay', type=int, default=10, help='Delay between each test, in minutes')
    parser.add_argument('--timezone', type=str, default='US/Pacific', help='Timezone to use for log timestamps')
    parser.add_argument('--timestamp-format', type=str, default='YY/MM/DD HH:mm:ss', help='Timezone format for logs. Excluding seconds (ss) may cause database errors.')
    parser.add_argument('--run-console-loop', type=str, default='y', choices=['y', 'n', 'Y', 'N'], help='Run in console loop (Y/n). "n" allows for the use of other task schedulers.')
    parser.add_argument('--dump-csv', action='store_true', help='Dump database to CSVs and exit')

    args = parser.parse_args()

    pnc = PyNetCheck(ping_count=args.ping_count,
                     ping_host=args.ping_host,
                     test_delay=args.test_delay,
                     db_filename=args.db_filename,
                     timezone=args.timezone,
                     timestamp_format=args.timestamp_format)

    try:
        if args.dump_csv:
            pnc.consprint('\nDumping database to CSVs...')
            pnc.dump_data_to_csv()
            pnc.consprint()

        elif args.run_console_loop.lower() == 'y':
            pnc.loop()

        else:
            pnc.run_once()

    except KeyboardInterrupt:
        pnc.consprint('\nDumping most recent data to CSVs...')
        pnc.dump_data_to_csv()
        pnc.consprint()
