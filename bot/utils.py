import re
from unidecode import unidecode
import filetype
from asyncio import Queue
from tqdm import tqdm
from telethon.tl.types import (
    Message,
    MessageEntityTextUrl,
    MessageEntityUrl,
)
import time

def empty_queue(queue: Queue):
  while not queue.empty():
    queue.get_nowait()
    queue.task_done()

def get_file_name(message: Message) -> str | None:
    if message.file and message.file.name:
        return message.file.name
    return None

def get_file_extension(file_path: str) -> str|None:
   # Detecta o tipo do arquivo com base no conteúdo
    kind = filetype.guess(file_path)
    if kind:
        return kind.extension

    print("Tipo de arquivo não detectado") 
    return None

def create_filter_files_regex(file_names: list, allowed_extensions: list) -> str:
    """
    Function to filter file name.

    Parameters:
    - file_names: List of files to search.
    - allowed_extensions: The extensions you want to search (como ['pdf', 'docx', 'txt']).

    Returns:
    - A regular expression: An uncompiled regex to find those files
    """

    # 1. Remove accents and convert to lower case
    normalized_names = [unidecode(name).lower() for name in file_names]
    # 2. Create the name patterns, search everything with those names
    names_pattern = ".*" + ".*|".join(normalized_names) + ".*"
    # 3. Create the extensions patterns
    extensions_pattern = "|".join(allowed_extensions)
    # 4. Create the final regex
    regex_pattern = r"^(" + names_pattern + r")\." + extensions_pattern + r"$"

    return regex_pattern

def create_progress_callback(start_time: float, desc: str = ""):
    progress_bar = tqdm(
        total=100,  
        unit='B',
        unit_scale=True,
        desc=desc,
        leave=True
    )

    # Retorna a função de callback
    def wrapped_progress_callback(received_bytes, total_bytes):
        progress = (received_bytes / total_bytes) * 100
        progress_bar.n = progress  
        progress_bar.last_print_n = progress
        progress_bar.update(0)  
        # Calculate the download speed to show, 
        progress_bar.set_postfix({
            'Speed': f"{(received_bytes / (time.time() - start_time)) / 1024 / 1024:.2f} MB/s"
        })
    
    return wrapped_progress_callback

def create_filter_links_regex(
    message_text: str, pattern_group_title: str = "all",
    ) -> str|None:
    
    
    normalized_pattern = unidecode(pattern_group_title).lower()
    pattern = rf"{normalized_pattern}"
    return pattern

class FileManager:
        
    def __init__(self) -> None:
        pass

class LinkManager:
    def __init__(self) -> None:
        self.link_patterns = r"""
            (https://t\.me/\+[^/]+)|   # Group 1: Private Telegram invite links
            (https://t\.me/[^/]+)|     # Group 2: Public Telegram links
            (https?://[^\s]+)          # Group 3: General internet links
        """

    def _search_links(
        self,
        message_text: str,
        entities: list,
        link_filters: dict,
    ) -> list:
        """
        Search for links in the message:
        - Hyperlinks (MessageEntityTextUrl)
        - Explicitly in the message text (MessageEntityUrl)
        """
        urls = []

        for entity in entities:
            if isinstance(entity, MessageEntityTextUrl):
                url: str = entity.url
                link_type = self._classify_link(url)
                if link_filters.get(link_type):
                    urls.append((url, link_type))

            elif isinstance(entity, MessageEntityUrl):
                url: str = message_text[
                    entity.offset : entity.offset + entity.length
                ]
                link_type = self._classify_link(url)
                if link_filters.get(link_type):
                    urls.append((url, link_type))

        return urls

    def _classify_link(self, link: str) -> str | None:
        match = re.match(self.link_patterns, link, re.VERBOSE)
        if match:
            if match.group(1):
                return "private"
            elif match.group(2):
                return "public"
            elif match.group(3):
                return "general"
        return None  # Not a valid link

    def search_link(
        self,
        message_text: str,
        message_entities: list | None,
        private: bool = True,
        public: bool = True,
        general: bool = False,
    ) -> list | None:
        """
        Search for Telegram links inside the provided text.

        Return:
        A list of tuples containing the link and the link type:
        [
            (link, link_type: "private"|"public"|"general"),
            ("https://t.me/...", "public"),
            ("https://t.me/+", "private"),
            ("https://www.example.com", "general"),
        ]
        """
        link_filters = {
            "private": private,
            "public": public,
            "general": general,
        }

        # If the message has no entities, it has no links
        if not message_entities:
            return None

        # Search for links explicitly in the text (e.g., https://xyz)
        links = self._search_links(message_text, message_entities, link_filters)
        return links

