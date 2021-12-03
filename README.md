simple telegram bot to upload torrent files and get stats from seedbox.

setup:
 - install all dependencies (pip install -r requirements.txt)
 - configure keys and tokens (run script once, it will generate config json)
 - verify channel/chat with `verify` command (so that only you are capable of uploading torrents to your seedbox)
 - run the script and hope nothing crashes
 - when using self-signed certs pass path to pem file with REQUESTS_CA_BUNDLE like 
```
REQUESTS_CA_BUNDLE=myCA.pem python3 script.py
```
