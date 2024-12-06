import re
from unidecode import unidecode
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from pyrogram.raw.base.message_entity import MessageEntity
import filetype

def get_file_name(message: Message) -> str | None:
    if not message.media:
        return None

    media_attr = getattr(message, message.media.value, None)
    if media_attr and hasattr(media_attr, "file_name"):
        return media_attr.file_name

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

def create_filter_links_regex(
    message_text: str, pattern_group_title: str = "all",
    ) -> str|None:
    
    
    normalized_pattern = unidecode(pattern_group_title).lower()
    pattern = rf"{normalized_pattern}"
    return pattern

class FileManager:
        
    def __init__(self) -> None:
        pass



# Needs some changes, just seeing how it behaves 
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
        entities: list[MessageEntity],
        link_filters: dict,
    ) -> list:

        """
        Search for links in the message:
        hyperlinks or embedded inside MessageEntityType.TEXT_LINK 
        explicty in the message text inside MessageEntityType.URL

        Note, Telegram does not embed explicty links in the entity
        to avoid redundancy, that's why we need to pass the text
        either way
        """

        urls = []

        for entity in entities:
            if entity.type == MessageEntityType.TEXT_LINK:
                url: str = entity.url
                link_type = self._classify_link(url)
                if link_filters.get(link_type):
                    urls.append((url, link_type))

            if entity.type == MessageEntityType.URL:
                url: str = message_text[
                    entity.offset : entity.offset + entity.length
                ]
                link_type = self._classify_link(url)
                if link_filters.get(link_type):
                    urls.append((url, link_type))

        return urls

    def _classify_link(self, link:str) -> str|None:
        match = re.match(self.link_patterns, link, re.VERBOSE)
        if match:
            if match.group(1):
                return "private"
            elif match.group(2):
                return "public"
            elif match.group(3):
                return "general"
        return None  # Not a valid link


    # FIX There's a better way to do it, feel free to improve
    def search_link(
        self,
        message_text: str,
        message_entities: list[MessageEntity]|None,
        private: bool = True,
        public: bool = True,
        general: bool = False,
    ) -> list|None:

        """Search for telegram link inside the text passed

        Return:
        A list of tuples, containing the link and the link_type e.g:
        [
            
            (link, link_type: "private"|"public"|"general")
            (https://t.me/..., "public")
            (https://t.me/+, "private")
            (https://www.example.com, "general")
            ...
        ]
        """

        link_filters = {
            "private": private,
            "public": public,
            "general": general,
        }

        # If the message has no entities has no links
        if not message_entities:
            return None

             # Search for links that are explicty in text e.g https://xyz
        links = self._search_links(message_text, message_entities, link_filters)
        return links


