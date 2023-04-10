import queue, threading
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks import CallbackManager
from langchain.memory import RedisChatMessageHistory
from serge.utils.llm import LlamaCpp

class ThreadedGenerator:
    def __init__(self):
        self.queue = queue.Queue()

    def __iter__(self):
        return self

    def __next__(self):
        item = self.queue.get()
        if item is StopIteration: raise item
        return item

    def send(self, data):
        self.queue.put(data)

    def close(self):
        self.queue.put(StopIteration)

class ChainStreamHandler(StreamingStdOutCallbackHandler):
    def __init__(self, gen):
        super().__init__()
        self.gen = gen

    def on_llm_new_token(self, token: str, **kwargs):
        self.gen.send(token)

def llm_thread(g, chat: LlamaCpp, prompt: str, history: RedisChatMessageHistory):
    try:
        chat.callback_manager = CallbackManager([ChainStreamHandler(g)])
        answer = chat(prompt)
    finally:
        try:
            history.add_ai_message(answer)
        except UnboundLocalError:
            pass
        g.close()


def stream(chat: LlamaCpp, prompt: str, history: RedisChatMessageHistory):
    g = ThreadedGenerator()
    threading.Thread(target=llm_thread, args=(g, chat, prompt, history)).start()
    return g


def get_prompt(history: RedisChatMessageHistory):
    prompt = ""

    for message in history.messages:
        match message.type:
            case "human":
                prompt += "### Instruction:\n" + message.content + "\n"
            case "ai":
                prompt += "### Response:\n" + message.content + "\n"
            case "system":
                prompt += "### System:\n" + message.content + "\n"
            case _:
                pass
    
    return prompt
