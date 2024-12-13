from bot.settings import Settings
from bot.rate_limit import TokenBucket
from bot.custom_client import CustomClient
from bot.config import ConfigParser
from bot.message_handler import MessageHandler
from bot.utils import (
    create_filter_files_regex,
    LinkManager,
    get_file_name,
    get_file_extension,
    progress,
    empty_queue
)
from pyrogram.types import (
    Message, Chat, ChatPermissions, ChatPreview
)
from pyrogram.errors import (
    ChatForwardsRestricted, FloodWait, FileReferenceExpired
)
import asyncio
import sys
from pathlib import Path
import os
from datetime import datetime

try:
    import uvloop
    uvloop.install()
except ModuleNotFoundError:
    print("uvloop not installed, it's not available to windows.\nConsider installing it if you can.")

class Bot(MessageHandler):

    def __init__(self):
        settings = Settings()
        self.messages_queue = asyncio.Queue()
        self.download_queue = asyncio.Queue()
        self.finished_queue = False
        self.finished_dequeue = False

        # Usefull in case of file_id expiration or save to continue later
        self.last_processed_msg = 0

        # Since rate limit is the amount of messages sended per minute
        seconds_in_minute = 60
        self.rate_limit = 60
        self.interval = seconds_in_minute / self.rate_limit

        self.bucket = TokenBucket(
            inicial_tokens=1,
            max_tokens=self.rate_limit,
            refill_interval=self.interval
        )
        
        # Define the download directory
        self.download_dir = Path('./downloads')
        self.download_dir.mkdir(exist_ok=True)

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
         
    async def _queue_messages(
        self, 
        origin_chat: Chat,
        offset_id: int = 0,
        limit: int = 100,
        reverse: bool = True,
        offset_date: datetime|None = None,
    ) -> None:
    
        try:
            async for message in self.get_chat_history(
                chat_id=origin_chat.id,
                reverse=reverse,
                limit=limit,
                offset_id=offset_id,
                #offset_date=offset_date
            ):

                if not message:
                    self.finished_queue = True
                    return

                print(f"Fetched message ID: {message.id}")
                await self.messages_queue.put(message)

        except FloodWait as e:
            print(f"FloodWait detected, it's normal. Waiting {e.value} seconds...")
            await asyncio.sleep(e.value)

        print("All messages fecthed")

    async def _queue_downloads(
        self, 
        message: Message,
    ) -> Message|None:
   

        # We first try to get from the telegram atribute
        # I added the message_id, to avoid filename conflicts
        # Since telegram can have two files with the same name in a group

        filename = f"message_{message.id}_{get_file_name(message)}"
        # If we don't provide a filename it will be random
        file_path = self.download_dir / (filename or f"{message.id}_temp")

        print("Started download message_id:", message.id)
        downloaded_file_path = await self.download_media(
            message, file_name=str(file_path), progress=progress
        )
        print("Finished download message_id:", message.id)
    
            
        # Sometimes the file in the telegram doesn't have filename
        # Which has the extension that is a requirement to telegram upload
        if not filename:
            extension = get_file_extension(downloaded_file_path)
            new_file_path = file_path.with_suffix(f".{extension}")
            os.rename(file_path, new_file_path)
            file_path = new_file_path
       
        await self.download_queue.put((message, file_path))

    async def _dequeue_messages(
        self,
        origin_chat: Chat,
        destiny_chat: Chat,
        topic_id: int|None = None,
        rate_limit: int = 20,
        offset_id: int = 0,
        offset_date: datetime | None = None
        
    ) -> None:
        
        self.last_processed_msg = offset_id

        while True:

            if self.messages_queue.empty():

                if self.finished_queue:
                    break

                await self._queue_messages(
                    origin_chat=origin_chat,
                    offset_id=self.last_processed_msg,
                    offset_date=offset_date,
                ) 

            message: Message = await self.messages_queue.get()

            while not self.bucket.consume():
                print("Preveting flood, waiting seconds:", self.interval)
                await asyncio.sleep(self.interval)

            try:
                await self._messages_trial(
                    destiny_group=destiny_chat, 
                    origin_group=origin_chat,
                    message=message,
                    topic_id=topic_id,
                )
           
            except FileReferenceExpired:
                print("File reference expired, refreshing...")
                empty_queue(self.messages_queue)
                empty_queue(self.download_queue)

            except Exception as e:
                print(f"Message trial error: {e}")
            
            finally:
                self.messages_queue.task_done()

        print("All messages processed")
        self.finished_dequeue = True

    async def _dequeue_downloads(
        self, 
        destiny_chat_id: int|str,
        reply_to_message_id: int|None = None
    ) -> Message|None:
        
        while True:
            if self.download_queue.empty():
                if self.finished_dequeue:
                    break
                await asyncio.sleep(5)
            
            message, file_path = await self.download_queue.get()

            while not self.bucket.consume():
                print("Flood await time:", self.interval)
                await asyncio.sleep(self.interval)
            
            try:
                print("Starting upload message_id:", message.id)
                await self._send_copy_message(
                    chat_id=destiny_chat_id,
                    message=message,
                    reply_to_message_id=reply_to_message_id,
                    file_path=file_path,
                )

            except Exception as e:
                print(f"Error while trying to download message: {e}")

            finally:
                self.download_queue.task_done()

            self.last_processed_msg = message.id
            print("Finished upload message_id:", message.id)
            os.remove(file_path)

        print("All medias uploaded")

    async def _messages_trial(
        self, 
        destiny_group: Chat,
        origin_group: Chat,
        message: Message,
        topic_id: int | None = None
    ) -> Message|None:

        if message.service: 
            print("Service message, ignoring message_id:", message.id)
            return
 
        # Send copy messages, it's same as a forward but, copying the
        # content, so it works for unrestricted and restricted content
        # Does't work with resctricted media, that we have to download

        protected_content_media = (
            (
                origin_group.has_protected_content or 
                message.has_protected_content 
            ) and message.media
        )

        if protected_content_media:
            return await self._queue_downloads(message)
        
        print("Copied message_id", message.id)
        sended_message = await self._send_copy_message(
            chat_id=destiny_group.id,
            message=message,
            reply_to_message_id=topic_id,
        )
        self.last_processed_msg = message.id
        return sended_message
        
    async def _validate_group(
        self, group_identifier: int|str
    ) -> Chat|ChatPreview: 
    
        try:
            origin_chat = await self.get_chat(group_identifier)
        except Exception as e:
            sys.exit(f"Error with group: {e}")
        
        return origin_chat
    
    async def _create_new_group(
        self, 
        group_title: str,
    ) -> Chat:
        
        new_group: Chat = await self.create_supergroup(
            title=group_title, 
        )
        
        # Allow new members of the group to see the old messages
        return new_group

    async def clone_messages(
        self, 
        origin_group_id: int|str,
        destiny_group_id: int|str|None = None,
        new_group_name: str|None = None,
        topic_id: int|None = None,
        offset_id: int = 0,
        offset_date: datetime | None = None
    ) -> None:
        
        
        origin_chat: Chat =  await self._validate_group(origin_group_id)    
        print(f"Origin group: {origin_chat.title} is alright")

        if not destiny_group_id:
            print("No destiny group provided creating a new one")
            if not new_group_name:
                print("No name provided, creating a default name")
                new_group_name = f"{origin_chat.title}-clone"
            
            destiny_group: Chat = await self._create_new_group(
                group_title=new_group_name,
            )
            destiny_group_id = destiny_group.id

        destiny_chat: Chat = await self._validate_group(destiny_group_id)
        print(f"Destiny group: {destiny_chat.title} is alright")

        await asyncio.gather(

            self._dequeue_messages(
                destiny_chat=destiny_chat,
                origin_chat=origin_chat,
                topic_id=topic_id,
                offset_id=offset_id,
                offset_date=offset_date,

            ),

            self._dequeue_downloads(
                destiny_chat_id=destiny_chat.id,
                reply_to_message_id=topic_id,
            ),
         )


async def main():
    bot = Bot()
    await bot.start()

    # Group to catch from
    origin_group = -1001889466238

    # Group to send to
    destiny_group = -1002070526963

    # Topic that you want to send
    topic_id = 7342
    
    # The last message it stoped
    offset_id = 308

    print("\n>>> Cloner up and running.\n")
    await bot.clone_messages(
        origin_group_id=origin_group,
        destiny_group_id=destiny_group,
        topic_id=topic_id,
        offset_id=offset_id
    )

    await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
