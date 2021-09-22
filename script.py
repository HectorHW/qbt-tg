import os
import string
import warnings

import telegram
from telegram.ext import Updater, Dispatcher, CallbackContext

import json
import sys

def load_config(filename):
    if not os.path.exists(filename):
        return None

    with open(filename) as f:
        content = json.load(f)

    return content

def save_config(config, filename):
    with open(filename, 'w') as f:
        json.dump(config, f, sort_keys=True, indent=4)

if __name__ == '__main__':
    
    n_args = len(sys.argv)

    if n_args==1:
        config_path = 'config.txt'
    elif n_args==2:
        config_path = sys.argv[1]
    else:
        print("usage: script.py [config_path]")
        sys.exit(1)
    
    print(f'config file : {config_path}')

    config = load_config(config_path)

    if config is None:
        print("could not load config file")
        print(f"creating sample config file with path '{config_path}'")
        
        config = {"tg_token":"abcd", "qbt_username":"admin", "qbt_password":"adminadmin", "chat_id":None}
        save_config(config, config_path)
        sys.exit(2)

    import qbittorrentapi as qbt
    qbt_client = qbt.Client(host='localhost:8080', username=config["qbt_username"], password=config["qbt_password"], VERIFY_WEBUI_CERTIFICATE=False)
    
    print(f"qbt version: {qbt_client.app.version}")

    updater = Updater(token=config["tg_token"], use_context=True)

    dispatcher:Dispatcher = updater.dispatcher

    import logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)

    def start(update, context):
        context.bot.send_message(chat_id=update.effective_chat.id, text="booba")

    from telegram.ext import CommandHandler

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)


    def get_load():
        import psutil
        return "load: %.2f %.2f %.2f" % psutil.getloadavg()

    def get_space():
        import shutil
        total, used, free = shutil.disk_usage("/media/verbatim")
        total_gib = total / 2**30
        free_gib = free / 2**30
        used_gib = used / 2**30
        return f"disk: {used_gib:.0f}/{total_gib:.0f} GiB\n({free_gib/total_gib*100:.1f}% free)"

    def get_service_status():
        import subprocess
        f = subprocess.Popen(['service', 'qbittorrent-nox', 'status'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        f.wait()

        s = ' '.join([item.decode('utf-8').strip() for item in f.stdout.readlines()])
        return s

    def get_system_uptime():
        t = os.popen('uptime -p').read()[:-1]
        return f"uptime:\n{t}"


    def get_system_status():
        load_str = get_load()
        space_str = get_space()
        qbt_status_str = get_service_status()
        uptime_str = get_system_uptime()
        return '\n'.join([load_str, space_str, uptime_str]), qbt_status_str

    def get_qbt_stats():
        try:
            global qbt_client
            stats_dict = qbt_client.transfer_info()
            up_speed = stats_dict['up_info_speed'] / 2**10
            down_speed = stats_dict['dl_info_speed'] / 2**10

            torrents_list = qbt_client.torrents_info()
            up_count = len([x for x in torrents_list if x['state']=='uploading'])
            down_count = len([x for x in torrents_list if x['state']=='downloading'])

            return f"{down_speed:.2f} KiB Down | {up_speed:.2f} KiB Up \n{up_count+down_count} active of {len(torrents_list)} total\n({down_count} downloading, {up_count} seeding)"
        

        except Exception as e:
            return "failed to get qbittorrent data"

    def status(update, context):
        global config
        if config["chat_id"] is not None and update.effective_chat.id==config["chat_id"]:
            text, qbt_status_str = get_system_status()
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"`{text}`", parse_mode=telegram.ParseMode.MARKDOWN)
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"service qbittorrent-nox status:\n`{qbt_status_str}`", parse_mode=telegram.ParseMode.MARKDOWN)
            qbt_stats = get_qbt_stats()
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"`{qbt_stats}`", parse_mode=telegram.ParseMode.MARKDOWN)



    dispatcher.add_handler(CommandHandler('status', status))

    def got_message(update, context):
        
        check_key(update.effective_message)
        check_file_confirm(update, context)

        if update.channel_post is not None and update.channel_post.text is not None:
            print(f"{update.channel_post.sender_chat.title}: {update.channel_post.text}")

        elif update.message is not None and update.message.text is not None: # message
            print(f"{update.message.from_user.username}: {update.message.text}")

    def check_file_confirm(update, context):
        global config
        if config['chat_id'] is not None and update.effective_chat.id==config['chat_id']:
            if context.chat_data.get('doc_info') is not None:
                doc_info = context.chat_data['doc_info']
                if update.effective_message.text is not None and update.effective_message.text.lower() in ['y', 'yes']:
                    
                    global qbt_client

                    with open('f.torrent', 'wb') as f:
                        f.write(context.chat_data['tmp_file'].getvalue())
                    try:
                        res = qbt_client.torrents_add(
                            torrent_files=context.chat_data['tmp_file'].getvalue(),
                            save_path='/media/verbatim/ftp_shared/torrents/',
                            )

                        context.bot.send_message(chat_id=update.effective_chat.id, text=res)
                    except Exception as e:
                        context.bot.send_message(chat_id=update.effective_chat.id, text=str(e))

                else:
                    context.bot.send_message(chat_id=update.effective_chat.id, text=f"canceled")
                context.chat_data['doc_info'] = None
                context.chat_data['tmp_file'].close()
            
    def got_file(update, context):
        global config

        if config['chat_id'] is not None and update.effective_chat.id==config['chat_id']:
            print("here")
            print(update.effective_message)
            
            print("sent document")
            doc_info = update.effective_message.document
            print(doc_info)
            if doc_info.mime_type=='application/x-bittorrent':
                context.chat_data['doc_info'] = doc_info
                
                response = prepare_file(update, context)

                context.bot.send_message(chat_id=update.effective_chat.id, text=response)
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text=f"mime type did not match, check file")
            return

    def prepare_file(update, context):
        doc_info = context.chat_data['doc_info']
        file_id = doc_info.file_id
        file_realname = doc_info.file_name
        file_handle: telegram.File = context.bot.get_file(file_id)
        
        import io
        mock_file = io.BytesIO()
        file_handle.download(out=mock_file)

        import libtorrent as lt
        info = lt.torrent_info(mock_file.getvalue())
        size_gb = info.total_size() / 2**30
        name = info.name()
        context.chat_data['tmp_file'] = mock_file
        return f"add {name} with size {size_gb:.1f} Gb?\n(y/yes to accept, _ to cancel)"



    from telegram.ext import MessageHandler, Filters

    msg_handler = MessageHandler(Filters.text & (~Filters.command), got_message)
    file_handler = MessageHandler(Filters.document, got_file)

    dispatcher.add_handler(file_handler)
    dispatcher.add_handler(msg_handler)

    updater.start_polling()

    CHAT_ID = config["chat_id"]
    AWAIT_SALT = False
    KEY = ''

    def command_verify():
        import random
        base = string.ascii_lowercase+string.digits
        global KEY
        KEY = ''.join(random.choice(base) for _ in range(8))
        global config


        print(f"generated key: {KEY}")
        global AWAIT_SALT

        while True:
            print("press ENTER to continue or type cancel to cancel verification")
            s = input()
            if s.lower()=='cancel':
                print('cancelled verification, set AWAIT_SALT to False')
                AWAIT_SALT = False
                return
            elif s=='':
                AWAIT_SALT = True
                print("set AWAIT_SALT to True")
                print("salt confirmed, now just type key in desired chat")
                return

    def check_key(msg:telegram.Message):

        global AWAIT_SALT

        if not AWAIT_SALT:
            return

        global config

        if msg.text is not None and msg.text==KEY:
            print(f'verified chat: {msg.chat.title or msg.chat.username}')
            config['chat_id'] = msg.chat.id
            print("set AWAIT_SALT to False")
            AWAIT_SALT = False
            
            global config_path

            save_config(config, config_path)

            print(f"overwritten config file {config_path}")


    def command_say(s:str):
        if CHAT_ID is None:
            warnings.warn("CHAT_ID is not set, provide it with config file or /verify")
        else:
            updater.bot.send_message(chat_id=CHAT_ID, text=s)


    help_msg = """
    
    say to type to saved chat
    
    verify to verify channel
    
    stop to stop the bot
    
    """
    print(help_msg)

    while True:


        s = input()

        if s=="stop":
            break
        if s.startswith("say"):
            command_say(s.split(' ', 1)[-1])

        elif s.startswith("verify"):
            command_verify()
        else:
            print(help_msg)

    updater.stop()

