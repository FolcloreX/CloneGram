from pyrogram.errors import FloodWait
from bot.settings import Settings
from bot.utils import create_filter_files_regex, LinkManager
from bot.config import ConfigParser
from pyrogram.types import (
    Message, Chat, ChatPermissions, ChatPreview, Photo
)
from tempfile import TemporaryDirectory
from unidecode import unidecode
from bot.custom_client import CustomClient
from bot.rate_limit import TokenBucket
import asyncio
import re
import sys
import uvloop
import inspect
from typing import Callable
from pathlib import Path
import tempfile
from io import BytesIO

uvloop.install()


class Bot(CustomClient):

    def __init__(self):
        settings = Settings()
        self.link_manager = LinkManager()
        self.messages_queue = asyncio.Queue()
        self.finished_queue = False
        self.finished_dequeue = False 
        
        """I don't know a better way conditionals seems so cumbersome
        Pyrogram should have a function send method in the message
        media_type value, maybe a monkeypatch solves this.
        Well if in the MessageType we add a send function callable
        Object, we can get rid of all this junk code. I'll look for
        it later
        """
        self.downloadable_media = {
            "photo": self.send_photo,
            "video": self.send_video,
            "audio": self.send_audio,
            "document": self.send_document,
            "sticker": self.send_sticker,
            "video_note": self.send_video_note,
            "voice": self.send_voice,
            "animation": self.send_animation,
        }
        
        self.non_downloadable_media = {
            "venue": self.send_venue,
            "contact": self.send_contact,
            "location": self.send_location,
            "poll": self.send_poll,
            "dice": self.send_dice
        }

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
        origin_group: int|str,
        offset_id: int = 0,
        limit: int = 50,
    ) -> None:
    
        try:
            async for message in self.get_chat_history(
                chat_id=origin_group, reverse=True
            ):  
                print(f"Fetched message ID: {message.id}")
                await self.messages_queue.put(message)
                

        except FloodWait as e:
            print(f"FloodWait detected. Waiting {e.value} seconds...")
            await asyncio.sleep(e.value)

        self.finished_queue = True

    async def _dequeue_messages(
        self,
        origin_group: int|str,
        destiny_group: int|str,
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
                    destiny_group=destiny_group, 
                    origin_group=origin_group,
                    message=message,
                    topic_id=topic_id,
                )

            except Exception as e:
                print(f"Error while trying to copy message: {e}")

            finally:
                self.messages_queue.task_done()

    async def _universal_media_sender(
        self,
        destiny_chat: int|str,
        message: Message,
        send_function: Callable,
    ) -> Message:

        kwargs = {
            "media": message.media,
            "caption": message.caption,  
            "caption_entities": message.caption_entities,  
            "reply_markup": message.reply_markup,
        }            
        
        # Get the function's allowed arguments
        signature = inspect.signature(send_function)
        valid_params = set(signature.parameters.keys())

        # Filter kwargs to match valid parameters
        # Basically parse through kwargs and see which keys are
        # in the send function arguments and if they have value
        # So every single valid argument, will be filled with respective
        # Value avoiding errors

        filtered_kwargs = {
            key: value for key, value in kwargs.items() if key in valid_params and value
        }
        
        # Call the function with filtered arguments
        sended_message: Message = await send_function(
            destiny_chat, **filtered_kwargs
        )

        return sended_message
    
    async def _messages_trial(
        self, 
        destiny_group: int | str, 
        message: Message,
        origin_group: int | str,
        topic_id: int | None = None
    ) -> None:
        """
        Processes a message and forwards or re-uploads it to the specified destination group.

        This method handles messages differently based on whether they have protected content 
        (i.e., forwarding restrictions) and whether their media content is downloadable.

        Args:
            destiny_group (int | str): The chat ID or username of the group where the message will be sent.
            message (Message): The original message object to process.
            origin_group (int | str): The chat ID or username of the group where the message originated.
            topic_id (int | None): Optional topic ID for threaded groups.

        Behavior:
            - If the message has protected content (`has_protected_content` is True):
                - For downloadable media types (e.g., photos, videos, documents):
                    - Downloads the media to a temporary directory.
                    - Re-uploads the media to the destination group using the appropriate send function.
                - For non-downloadable content:
                    - Copies the message content and sends it to the destination group using the corresponding method.
            - If the message does not have protected content:
                - Copies the message directly from the origin group to the destination group using `copy_message`.
        """
        # Extract the media type from the message if there's one

        download_func = None
        non_download_func = None
        sended_message = None

        if message.media:

            media_type = str(message.media).lower().split('.')[1]

            download_func = self.downloadable_media.get(
                media_type, False
            )
            
            non_download_func = self.non_downloadable_media.get(
                media_type, False
            )

        # Check if the group has forward enabled
        if message.has_protected_content:
            print("Protected content")
                        
            # Handle downloadable media
            if download_func:
                print("Downloading Message:", message.id)
                tempfile.tempdir = './.cache'
                
                # Create a temporary directory for storing the downloaded file
                with TemporaryDirectory() as temp_dir:
                    file_path = f"{Path(temp_dir)}/"

                    # Download the media
                    downloaded_message = await self.download_media(
                        message, 
                        file_name=file_path,
                        block=True,
                    )

                    # Send the downloaded media to the destination group
                    sended_message = await self._universal_media_sender(
                        destiny_group, downloaded_message, download_func
                    )

            # Handle non-downloadable media
            else:
                print("Copying non-downloable message")
                sended_message = await self._universal_media_sender(
                    destiny_chat=destiny_group,
                    message=message,
                    send_function=non_download_func,
                )
        
        # Directly copy messages if there are no forwarding restrictions
        else:
            sended_message = await self.copy_message(
                chat_id=destiny_group,
                from_chat_id=origin_group,
                message_id=message.id,
                caption=message.caption,
                caption_entities=message.caption_entities,
                reply_to_message_id=topic_id,
            )
        
        # Set the same messages pinned as well
        if message.pinned_message:
            await self.pin_chat_message(
                chat_id=destiny_group,
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
        origin_group: int|str,
        destiny_group: int|str|None = None,
        new_group_name: str|None = None,
        topic_id: int|None = None,

    ) -> None:
        
        
        origin_chat = await self._validate_group(origin_group)    
        print(f"Origin group: {origin_chat.title} is alright")

        if not destiny_group:
            print("No destiny group provided creating a new one")
            if not new_group_name:
                print("No name provided, creating a default name")
                new_group_name = f"{origin_chat.title}-clone"
            
            new_group = await self._create_new_group(
                group_title=new_group_name,
            )

            destiny_group = new_group.id

        destiny_chat = await self._validate_group(destiny_group)
        print(f"Destiny group: {destiny_chat.title} is alright")

        await asyncio.gather(
            self._queue_messages(
                origin_group=origin_group,
            ),

            self._dequeue_messages(
                destiny_group=destiny_group,
                origin_group=origin_group,
                topic_id=topic_id
            )
        )

        print("Cloned sucessfuly")
    

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
    origin_group = -1001895953243
    #destiny_group = -1002246324969

    await bot.clone_messages(
        origin_group=origin_group,
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
