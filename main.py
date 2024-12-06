from bot.settings import Settings
from bot.rate_limit import TokenBucket
from bot.custom_client import CustomClient
from bot.config import ConfigParser
from bot.message_handler import MessageHandler
from bot.utils import (
    create_filter_files_regex,
    LinkManager,
    get_file_name,
    get_file_extension
)
from pyrogram.types import (
    Message, Chat, ChatPermissions, ChatPreview
)
from pyrogram.errors import ChatForwardsRestricted, FloodWait
import asyncio
import re
import sys
import uvloop
from pathlib import Path
import tempfile
import shutil
import os
from datetime import datetime

uvloop.install()

class Bot(MessageHandler):

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
         
    async def _queue_messages(
        self, 
        origin_chat: Chat,
        offset_id: int = 0,
        limit: int = 50,
        reverse: bool = True,
        offset_date: datetime|None = None,
    ) -> None:
    
        try:
            async for message in self.get_chat_history(
                chat_id=origin_chat.id,
                reverse=reverse,
            ):  

                print(f"Fetched message ID: {message.id}")
                await self.messages_queue.put(message)
                

        except FloodWait as e:
            print(f"FloodWait detected. Waiting {e.value} seconds...")
            await asyncio.sleep(e.value)

        self.finished_queue = True

    async def _dequeue_messages(
        self,
        origin_chat: Chat,
        destiny_chat: Chat,
        topic_id: int|None = None,
        rate_limit: int = 20,
    ) -> None:
        
        
        # Since rate limit is the amount of messages sended per minute
        # It defines the time interval to send each message
        seconds_in_minute = 60
        interval = (seconds_in_minute / rate_limit)

        # rate_limit Messages per Minute
        bucket = TokenBucket(
            inicial_tokens=1,
            max_tokens=rate_limit,
            refill_interval=interval
        )
 
        while True:
        
            if self.messages_queue.empty():
                if self.finished_queue:
                    return
                await asyncio.sleep(5)

            message: Message = await self.messages_queue.get()

            while not bucket.consume():
                await asyncio.sleep(interval)

            try:
                await self._messages_trial(
                    destiny_group=destiny_chat, 
                    origin_group=origin_chat,
                    message=message,
                    topic_id=topic_id,
                )

            except Exception as e:
                print(f"Error while trying to copy message: {e}")

            finally:
                self.messages_queue.task_done()
    
    async def _protected_content_deal(
        self, 
        message: Message,
        destiny_chat_id: int|str,
        reply_to_message_id: int|None = None
    ) -> Message|None:
        
        # Creates a temporary directory
        temp_dir = tempfile.mkdtemp(dir='./.cache')
        print("Processing message_id:", message.id)

        try:
            # We first try to get from the telegram atribute
            filename = get_file_name(message)
            # If we don't provide a filename it will be random
            file_path = Path(temp_dir) / (filename or f"{message.id}_temp")
            downloaded_message = await self.download_media(
                message, file_name=str(file_path)
            )
            print("Downloaded file:", downloaded_message)
            
        except ValueError:
            print("Non donwloable media, just sending")
            return await self._send_copy_message(
                chat_id=destiny_chat_id,
                message=message,
                reply_to_message_id=reply_to_message_id
            )

        # It'll try to take the file extension from it's metadata
        if not filename:
            extension = get_file_extension(downloaded_message)
            new_file_path = file_path.with_suffix(f".{extension}")
            print(f"extension:{extension}\nnewfile:{new_file_path}")
            os.rename(downloaded_message, new_file_path)
            downloaded_message = new_file_path

        return await self._send_copy_message(
            chat_id=destiny_chat_id,
            message=message,
            reply_to_message_id=reply_to_message_id,
            file_path=downloaded_message,
        )


    async def _non_protected_content_deal(
        self,
        message: Message,
        origin_chat_id: int|str,
        destiny_chat_id: int|str,
        reply_to_message_id: int|None = None
    ) -> Message|None:
        try:
            print("Forward allowed, copying message_id:", message.id)
            return await self.copy_message(
                chat_id=destiny_chat_id,
                from_chat_id=origin_chat_id,
                message_id=message.id,
                caption=message.caption,
                caption_entities=message.caption_entities,
                reply_to_message_id=reply_to_message_id,
            ) 

        # In case the message is restricted
        except ChatForwardsRestricted:
            print(f"Message {message.id} is restricted from forwarding.")
            return await self._protected_content_deal(
                message=message,
                destiny_chat_id=destiny_chat_id,
                reply_to_message_id=reply_to_message_id
            )


    async def _messages_trial(
        self, 
        destiny_group: Chat,
        origin_group: Chat,
        message: Message,
        topic_id: int | None = None
    ) -> None:
        
        if message.service:
            print("Service message, ignoring message_id:", message.id)
            return

        # FIX I have to improve this logic, it's not necessaire to
        # Check if everytime, only once, but it's always necessaire to 
        # Test if the message is restricted or not, but I think a error
        # Manager is better than a conditional

        # In case the group is restricted
        if origin_group.has_protected_content:
            sended_message = await self._protected_content_deal(
                message, destiny_group.id, topic_id
            )
        
        # In case the group is not restricted
        else:
            sended_message = await self._non_protected_content_deal(
                message, destiny_group.id, topic_id
            )

        # Set the same messages pinned as well
        if message.pinned_message:
            await self.pin_chat_message(
                chat_id=destiny_group.id,
                message_id=sended_message.id,
                disable_notification=True
            )
          
   
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
    ) -> None:
        
        
        origin_chat = await self._validate_group(origin_group_id)    
        print(f"Origin group: {origin_chat.title} is alright")

        if not destiny_group_id:
            print("No destiny group provided creating a new one")
            if not new_group_name:
                print("No name provided, creating a default name")
                new_group_name = f"{origin_chat.title}-clone"
            
            destiny_group = await self._create_new_group(
                group_title=new_group_name,
            )
            destiny_group_id = destiny_group.id

        destiny_chat = await self._validate_group(destiny_group_id)
        print(f"Destiny group: {destiny_chat.title} is alright")

        await asyncio.gather(
            self._queue_messages(
                origin_chat=origin_chat,
            ),

            self._dequeue_messages(
                destiny_chat=destiny_chat,
                origin_chat=origin_chat,
                topic_id=topic_id
            )
        )

        print("Cloned sucessfuly")
    

async def main():
    bot = Bot()
    await bot.start()
    origin_group = -1002410566093
    #destiny_group = -1002246324969
    print("\n>>> Cloner up and running.\n")
    await bot.clone_messages(
        origin_group_id=origin_group,
    )



if __name__ == "__main__":
    asyncio.run(main())
