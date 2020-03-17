from main import con
import json
import random
import string


class NewChatBot:
    def __init__(self):
        self.db = con["chatbot_data"]
        self.smalltalk = json.loads(open("data/smalltalk.json").read(), encoding="utf-8")

    def convert_trigger(self, message):
        message = message.lower()
        to_replace = list(string.digits + string.ascii_lowercase + "äüöß")
        for l in string.printable:
            if l not in to_replace and l in list(message):
                message = message.replace(l, '')
        return message

    def get_response(self, message):
        result = self.db.find_one({"_id": self.convert_trigger(message)})
        if result:
            responses = sorted(result["responses"], key=lambda k: result["responses"][k], reverse=True)
            return responses[0]
        return random.choice(self.smalltalk)

    def process_response(self, trigger, response):
        self.db.update({"_id": self.convert_trigger(trigger)}, {"$inc": {"uses": 1, f"responses.{response.replace('.', '#PUNKT#')}": 1}}, upsert=True)
