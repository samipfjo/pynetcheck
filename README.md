# pynetcheck
Scheduled ping checks and speedtests with data persistence.

Currently tested on Windows 10 and Ubuntu. Other flavors of Linux will almost certainly work, and macOS may, too.

&nbsp;

### Setup
  Requires `arrow` and `speedtest-cli`, which can be gotten from the requirements file:
  
    pip install -r requirements.txt

&nbsp;
### Usage
  Requires Python 3.6+
  
    python netcheck.py
        --ping-host [www.google.com] ~ Hostname or ip to ping
        --db-filename [connection_data.sqlite] ~ Database filename
        --ping-count [25] ~ Number of pings to perform during each test
        --timezone [US/Pacific] ~ Timezone to use for log timestamps
        --timestamp-format [YY/MM/DD HH:mm:ss] ~ Timezone format for logs. Excluding seconds (ss) may cause database errors.
        --run-console-loop (Y/n) ~ Run in a loop that pretty-prints output. "n" allows for the use of other task schedulers.
        --test-delay [10] ~ Delay between each test, in minutes
  
  Exit with ctrl+c, upon which the data will be dumped to two tab-delimited CSVs
