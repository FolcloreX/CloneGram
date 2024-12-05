from bot.custom_client import CustomClient
from pyrogram.types import Message
from pyrogram.enums import MessageMediaType

class MessageHandler(CustomClient):
    async def _send_copy_message(
            self, 
            chat_id: int|str,
            message: Message,
            reply_to_message_id: int|None,
            file_path: str|None = None
        ) -> Message|None:

        """
        Process a Pyrogram message and call the selfropriate send function for its media.

        Args:
            message (Message): The Pyrogram message object to process.
        """

        # This shit is so fucking ugly
        match message.media:

            # Downloable Medias
            case MessageMediaType.VIDEO:
                return await self.send_copy_video(
                    chat_id=chat_id, 
                    message=message, 
                    reply_to_message_id=reply_to_message_id,
                    file_path=file_path
                )
            case MessageMediaType.PHOTO:
                return await self.send_copy_photo(
                    chat_id=chat_id, 
                    message=message, 
                    reply_to_message_id=reply_to_message_id,
                    file_path=file_path
                )
            case MessageMediaType.DOCUMENT:
                return await self.send_copy_document(
                    chat_id=chat_id, 
                    message=message, 
                    reply_to_message_id=reply_to_message_id,
                    file_path=file_path
                )
            case MessageMediaType.AUDIO:
                return await self.send_copy_audio(
                    chat_id=chat_id, 
                    message=message, 
                    reply_to_message_id=reply_to_message_id,
                    file_path=file_path
                )
            case MessageMediaType.VOICE:
                return await self.send_copy_voice(
                    chat_id=chat_id, 
                    message=message, 
                    reply_to_message_id=reply_to_message_id,
                    file_path=file_path
                )
            case MessageMediaType.ANIMATION:
                return await self.send_copy_animation(
                    chat_id=chat_id, 
                    message=message, 
                    reply_to_message_id=reply_to_message_id,
                    file_path=file_path
                )
            # Non downloable medias, we just copy
            case MessageMediaType.STICKER:
                return await self.send_copy_sticker(
                    chat_id=chat_id,
                    message=message,
                    reply_to_message_id=reply_to_message_id
                )

        return await self.send_copy_text_message(
            chat_id=chat_id,
            message=message,
            reply_to_message_id=reply_to_message_id
        ) 

    async def send_copy_text_message(
        self,
        chat_id: int|str,
        message: Message,
        reply_to_message_id: int|None = None
    ) -> Message:
        """
        Sends a text message based on the Message object.

        Args:
            self: Pyrogram client.
            message: Message object containing the data.
        """
        return await self.send_message(
            chat_id=message.chat.id,
            text=message.text,
            reply_to_message_id=reply_to_message_id,
        )

    async def send_copy_photo(
        self,
        chat_id: int|str,
        message: Message,
        reply_to_message_id: int|None = None,
        file_path: str|None = None
    ) -> Message|None:
        """
        Sends a photo based on the Message object.

        Args:
            self: Pyrogram client.
            message: Message object containing the data.
        """
        return await self.send_photo(
            chat_id=message.chat.id,
            photo= file_path or message.photo.file_id,
            caption=message.caption,
            reply_to_message_id=reply_to_message_id,
        )

    async def send_copy_video(
        self,
        chat_id: int|str,
        message: Message,
        reply_to_message_id: int|None = None,
        file_path: str|None = None
    ) -> Message|None:
        """
        Sends a video based on the Message object.

        Args:
            self: Pyrogram client.
            message: Message object containing the data.
        """
        return await self.send_video(
            chat_id=message.chat.id,
            video=file_path or message.video.file_id,
            caption=message.caption,
            duration=message.video.duration,
            width=message.video.width,
            height=message.video.height,
            reply_to_message_id=reply_to_message_id,
        )


    async def send_copy_document(
        self,
        chat_id: int|str,
        message: Message,
        reply_to_message_id: int|None = None,
        file_path: str|None = None
    ) -> Message|None:
        """
        Sends a document based on the Message object.

        Args:
            self: Pyrogram client.
            message: Message object containing the data.
        """
        return await self.send_document(
            chat_id=message.chat.id,
            document=file_path or message.document.file_id,
            caption=message.caption,
            reply_to_message_id=reply_to_message_id,
        )

    async def send_copy_audio(
        self,
        chat_id: int|str,
        message: Message,
        reply_to_message_id: int|None = None,
        file_path: str|None = None
    ) -> Message|None:
        """
        Sends an audio file based on the Message object.

        Args:
            self: Pyrogram client.
            message: Message object containing the data.
        """
        return await self.send_audio(
            chat_id=chat_id,
            audio=file_path or message.audio.file_id,
            caption=message.caption,
            duration=message.audio.duration,
            performer=message.audio.performer,
            title=message.audio.title,
            reply_to_message_id=reply_to_message_id,
        )


    async def send_copy_voice(
        self,
        chat_id: int|str,
        message: Message,
        reply_to_message_id: int|None = None,
        file_path: str|None = None
    ) -> Message|None:
        """
        Sends a voice note based on the Message object.

        Args:
            self: Pyrogram client.
            message: Message object containing the data.
        """
        return await self.send_voice(
            chat_id=chat_id,
            voice=file_path or message.voice.file_id,
            caption=message.caption,
            duration=message.voice.duration,
            reply_to_message_id=reply_to_message_id,
        )


    async def send_copy_animation(
        self,
        chat_id: int|str,
        message: Message,
        reply_to_message_id: int|None = None,
        file_path: str|None = None
    ) -> Message|None:
        """
        Sends an animation (GIF) based on the Message object.

        Args:
            self: Pyrogram client.
            message: Message object containing the data.
        """
        return await self.send_animation(
            chat_id=chat_id,
            animation=file_path or message.animation.file_id,
            caption=message.caption,
            duration=message.animation.duration,
            width=message.animation.width,
            height=message.animation.height,
            reply_to_message_id=reply_to_message_id,
        )

    async def send_copy_sticker(
        self,
        chat_id: int|str,
        message: Message,
        reply_to_message_id: int|None = None
    ) -> Message|None:
        """
        Sends a sticker.

        Args:
            self: Pyrogram client.
            chat_id: ID of the chat or username.
            sticker: ID, file path, or URL of the sticker.
            kwargs: Optional arguments.
        """
        return await self.send_sticker(
            chat_id=chat_id,
            sticker=message.sticker.file_id,
            reply_to_message_id=reply_to_message_id,
            reply_markup=message.reply_markup,
        )


    async def send_copy_media_group(
        self, chat_id: int | str,
        message: Message,
        media_group: list,
        reply_to_message_id: int|None = None
    ) -> list[Message]:
        """
        Sends a media group based on the Message object.

        Args:
            self: Pyrogram client.
            message: Message object containing the data.
            media_group: List of InputMedia (InputMediaPhoto or InputMediaVideo).
        """
        return await self.send_media_group(
            chat_id=chat_id,
            media=media_group,
            reply_to_message_id=reply_to_message_id,
        )
   
