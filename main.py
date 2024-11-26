from pyrogram import Client, filters
from pyrogram import enums
from pyrogram import utils
from pyrogram.errors import FloodWait
from bot.settings import Settings
from bot.utils import create_filter_files_regex
from bot.utils import LinkManager
from pyrogram.types import Message
from unidecode import unidecode
import asyncio
import re
import sys
import uvloop
uvloop.install()

# Due to the telegram issue 1314 INVALID PEER ERROR
def get_peer_type_new(peer_id: int) -> str:
    peer_id_str = str(peer_id)
    if not peer_id_str.startswith("-"):
        return "user"
    elif peer_id_str.startswith("-100"):
        return "channel"
    else:
        return "chat"

utils.get_peer_type = get_peer_type_new


class Bot(Client):

    def __init__(self):
        settings = Settings()
        self.link_manager = LinkManager()
        self.messages_queue = asyncio.Queue()
        self.finished_queue = False
        self.finished_dequeue = False 
    
        # Get API keys at https://my.telegram.org/auth
        super().__init__(
            name=settings.account_name,
            phone_number=settings.phone_number,
            password=settings.password,
            api_id=settings.api_id,
            api_hash=settings.api_hash,
            plugins=dict(root='bot/plugins'),
            sleep_threshold=180
        )
        
    async def _messages_trial(self, regex:str, message: Message):

        if message.document:
            file_name = message.document.file_name
            if re.match(regex, unidecode(file_name).lower()):
                print(f"Matched file: {file_name}")
                await self.messages_queue.put(message.id)
            
        if message.text:
            # print("Analizying Text Message", message.id)
            link = self.link_manager.search_link(
                message_text=message.text,
                message_entities=message.entities
            )
            if link:
                print(link)
           
        #if message.photo:
        #    print("Analizying Photo Message", message.id)
        #    link = self.link_manager.search_link(
        #        message=message.caption,
        #        entities=message.caption_entities
        #    )
        #    print(link)

    async def _queue_messages(
        self, 
        origin_group: int|str,
        regex: str,
        offset_id: int = 0,
        limit: int = 50,
        topic_id: int|None = None
    ) -> None:

        try:
            async for message in self.get_chat_history(origin_group):
               await self._messages_trial(regex, message) 
            
        except FloodWait as e:
            print(f"FloodWait detected. Waiting {e.value} seconds...")
            await asyncio.sleep(e.value)

        finally:
            self.message_queue = True
 
    async def _dequeue_messages(
        self, 
        destiny_group: int|str, 
        origin_group: int|str,
        topic_id: int|None = None
    ) -> None:

        num = 0
        while True:
            print("rodando:", num) 

            if self.messages_queue.empty():
                if self.finished_queue:
                    return
                await asyncio.sleep(5)

            # A good measure to avoid being restricted
            if num % 20 == 0 and num != 0:
                await asyncio.sleep(60) 

            message_id = await self.messages_queue.get()
            num += 1

            try:
                await self.copy_message(
                    chat_id=destiny_group,
                    from_chat_id=origin_group,
                    message_id=message_id,
                    reply_to_message_id=topic_id
                )

                print("message sended")

            except Exception as e:
                print(f"Error while trying to copy message: {e}")

            finally:
                self.messages_queue.task_done()            

    async def clone_messages(
        self, 
        origin_group: int|str,
        destiny_group: int|str,
        regex: str,
        offset_id: int = 0,
        limit: int = 50,
        topic_id: int|None = None
    ) -> None:

        try:
            origin_chat = await self.get_chat(origin_group)
            print(f"The origin chat: {origin_chat.title} is alright")
        except Exception as e:
            sys.exit(f"Error with origin group: {e}")

        try:
            destiny_chat = await self.get_chat(destiny_group)
            print(f"The destiny chat: {destiny_chat.title} is alright")
        except Exception as e:
            print(f"Error with destiny group: {e}")
        
        await asyncio.gather(
            self._queue_messages(
                origin_group=origin_group, regex=regex
            ),

            self._dequeue_messages(
                destiny_group=destiny_group,
                origin_group=origin_group,
                topic_id=topic_id
            )
        )
        print("Congratulations the program finished alllright gigygri hoo yea")

async def main():
    bot = Bot()
    await bot.start()
    
    file_names = [
        'Aventuras na História',
        'Mente Afiada',
        'Veja',
    ]
    allowed_extensions = ['pdf']

    regex_pattern = create_filter_files_regex(file_names, allowed_extensions)
    origin_group = -1001923606985
    destiny_group = -1002246324969

    await bot.clone_messages(
        origin_group=origin_group,
        destiny_group=destiny_group,
        regex=regex_pattern,
    )


    print("\n>>> Bot up and running.\n")

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        await bot.stop()
        print("\n>>> Bot turn off.\n")

if __name__ == "__main__":
    asyncio.run(main())
