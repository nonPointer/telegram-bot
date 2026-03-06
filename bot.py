import requests
import time
import threading
import sys
import re
from pprint import pprint


bot_token = ""
bot_api_base_url = "https://api.telegram.org/bot{}".format(bot_token)

print_lock = threading.Lock()


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
                if self.stop_event.is_set():
                    break
                with print_lock:
                    print('\r' + symbol, end='', flush=True)
                time.sleep(duration)

        with print_lock:
            print("\r", end='')

def handle_edited_message(bot, message):
    pass

def handle_message(bot, message):
    text = message["message"].get("text")
    if not text:
        return
    # is a + b regex
    if re.match(r"^\d+\s*\+\s*\d+$", text):
        a, b = map(int, re.findall(r"\d+", text))
        bot.send_message(message["message"]["chat"]["id"], a + b)


class Bot():
    def log(self, message):
        with print_lock:
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
        stop_event = threading.Event()
        loading = threading.Thread(target=rotating_loading(stop_event).start)
        loading.start()
        try:
            response = requests.get(bot_api_base_url + "/getUpdates", data=params, timeout=params["timeout"] + 1)
            stop_event.set()
            loading.join()

            if response.status_code != 200:
                self.log(f"Error: {response.status_code}")
                return {"result": []}
        except KeyboardInterrupt:
            stop_event.set()
            loading.join()
            self.log("Exiting...")
            exit()
        except Exception as e:
            stop_event.set()
            loading.join()
            self.log(e)
            self.log("Timeout or Connection Error")
            return {"result": []}
        return response.json()

    def send_message(self, chat_id, text):
        data = {
            "chat_id": chat_id,
            "text": text
        }
        try:
            response = requests.post(bot_api_base_url + "/sendMessage", data=data)
            return response.json()
        except Exception as e:
            self.log(f"Failed to send message: {e}")
            return None

    def main(self):
        updates = self.get_updates()
        edited_message = list(
            filter(lambda x: "edited_message" in x, updates["result"]))
        messages = list(filter(lambda x: "message" in x, updates["result"]))

        if self.debug:
            pprint(updates)

        for message in edited_message:
            self.update_id = message["update_id"]
            handle_edited_message(self, message)
            self.log(message)

        for message in messages:
            self.update_id = message["update_id"]

            chat_id = message["message"]["chat"]["id"]
            first_name = message["message"]["chat"].get("first_name", "")
            last_name = message["message"]["chat"].get("last_name", "")
            username = message["message"]["chat"].get("username", "")

            text = message["message"].get("text")

            fmt = f"{bcolors.OKBLUE}[{chat_id}]{bcolors.ENDC} {first_name} {last_name} (@{username}):"
            if text:
                hd = threading.Thread(target=handle_message, args=(self, message))
                hd.start()
                self.log(f"{fmt} {text}")
            else:
                obj = {k: v for k, v in message['message'].items() if k not in [
                    'chat', 'date', 'from', 'message_id']}
                self.log(f"{fmt} {obj}")

    def start(self):
        while True:
            self.main()


if __name__ == "__main__":
    debug = False
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        debug = True

    bot = Bot(debug)

    if debug:
        bot.log("Debug mode")

    try:
        bot.start()
    except KeyboardInterrupt:
        bot.log("Exiting...")
