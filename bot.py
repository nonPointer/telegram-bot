import requests
import time
import threading
import time
import sys
import re
from pprint import pprint


bot_token = ""
bot_api_base_url = "https://api.telegram.org/bot{}".format(bot_token)


class bcolors():
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class rotating_loading():
    def __init__(self, stop_event: threading.Event):
        self.stop_event = stop_event

    def start(self):
        symbols = ['/', '-', '\\', '|']
        duration = 0.2
        while not self.stop_event.is_set():
            for symbol in symbols:
                print('\r' + symbol, end='', flush=True)
                time.sleep(duration)

        print("\r", end='')

def handle_edited_message(message):
    pass

def handle_message(message):
    # is a + b regex
    if re.match(r"^\d+\s*\+\s*\d+$", message["message"]["text"]):
        a, b = map(int, re.findall(r"\d+", message["message"]["text"]))
        bot.send_message(message["message"]["chat"]["id"], a + b)
    pass


class Bot():
    def log(self, message):
        print(
            f"{bcolors.OKGREEN}[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}]{bcolors.ENDC}", end="")
        if isinstance(message, str):
            print(" " + message)
        else:
            print()
            pprint(message)

    def __init__(self, debug: bool = False):
        self.update_id = 0
        self.debug = debug

    def get_updates(self):
        params = {
            "offset": self.update_id + 1,
            "timeout": 30
        }
        try:
            stop_event = threading.Event()
            loading = threading.Thread(target=rotating_loading(stop_event).start)
            loading.start()
            response = requests.get(bot_api_base_url + "/getUpdates", data=params, timeout=params["timeout"] + 1)
            stop_event.set()
            loading.join()

            if response.status_code != 200:
                self.log(f"Error: {response.status_code}")
                return {"result": []}
        except KeyboardInterrupt:
            self.log("Exiting...")
            exit()
        except Exception as e:
            self.log(e)
            self.log("Timeout or Connection Error")
            return {"result": []}
        return response.json()

    def send_message(self, chat_id, text):
        data = {
            "chat_id": chat_id,
            "text": text
        }
        response = requests.post(bot_api_base_url + "/sendMessage", data=data)
        return response.json()

    def main(self, ):
        updates = self.get_updates()
        edited_message = list(
            filter(lambda x: "edited_message" in x, updates["result"]))
        messages = list(filter(lambda x: "message" in x, updates["result"]))

        if self.debug:
            pprint(updates)

        for message in edited_message:
            self.update_id = message["update_id"]
            self.log(message)

        for message in messages:
            # self.log(message)

            self.update_id = message["update_id"]

            chat_id = message["message"]["chat"]["id"]
            first_name = message["message"]["chat"]["first_name"] if "first_name" in message["message"]["chat"] else ""
            last_name = message["message"]["chat"]["last_name"] if "last_name" in message["message"]["chat"] else ""
            username = message["message"]["chat"]["username"] if "username" in message["message"]["chat"] else ""

            text = message["message"]["text"] if "text" in message["message"] else None

            fmt = f"{bcolors.OKBLUE}[{chat_id}]{bcolors.ENDC} {first_name} {last_name} (@{username}):"
            if text:
                hd = threading.Thread(target=handle_message, args=(message,))
                hd.start()
                self.log(f"{fmt} {text}")
            else:
                obj = {k: v for k, v in message['message'].items() if k not in [
                    'chat', 'date', 'from', 'message_id']}
                self.log(f"{fmt} {obj}")

        # self.log(messages)

    def start(self):
        while True:
            self.main()


if __name__ == "__main__":
    bot = Bot()

    debug = False
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        bot.log("Debug mode")
        debug = True
        

    try:
        th = Bot(debug)
        th.start()
    except KeyboardInterrupt:
        bot.log("Exiting...")
