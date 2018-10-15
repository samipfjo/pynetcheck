# pynetcheck
Scheduled ping checks and speedtests with data persistence. Currently supports Windows and Linux, though macOS and others may be supported as well.

&nbsp;

### Setup
  Requires `arrow` and `speedtest-cli`, which can be gotten from the requirements file:
  
    pip install -r requirements.txt

&nbsp;
### Usage
  Requires Python 3.6+
  
    python netcheck.py
  
  Exit with ctrl+c, upon which the data will be dumped to two tab-delimited CSVs
