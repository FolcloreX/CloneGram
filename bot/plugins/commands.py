from functools import partial
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram import Client, enums

command = partial(filters.command, prefixes=list('/'))


@Client.on_message(command('start'))
async def start_command(client: Client, message: Message):
    await message.reply(
        'O nível intelectual do grupo transcendera o conceitual, ' 
        'mergulhando na essência do conhecimento profundo ' 
        'e da compreensão além das ideias convencionais.'
    )



