simple telegram bot to upload torrent files and get stats from seedbox.

requirements:
 - psutil to get system stats (`pip install psutil`)
 - telegram api (`pip install python-telegram-bot`)
 - libtorrent python wrapper (`sudo apt-get install python3-libtorrent`)
 - qbittorrent python api (`pip install qbittorrent-api`)

setup:
 - install all dependencies
 - configure keys and tokens (run script once, it will generate config json)
 - verify channel/chat with `verify` command (so that only you are capable of uploading torrents to your seedbox)
 - run the script and hope nothing crashes
