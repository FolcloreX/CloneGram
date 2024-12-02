import configparser

class ConfigParser:
    def __init__(self) -> None:
        self.config = configparser.ConfigParser()
        self.config_file = 'TgTracker.conf'
    
    def _create_new_conf(self, group_id: int, group_title: str) -> None:
        # Create a file with the session or agreggate a new session
        self.config.add_section(f'{group_id}')
        self.config.set(f'{group_id}', 'group_title', f'{group_title}')
        self.config.set(f'{group_id}', 'last_message', '0')

        with open(self.config_file, "w") as file:
            self.config.write(file)

    def _get_session(self, session_name: str) -> dict:
        # Return a dictionary containing all the key:values in a session
        return {key: value for key, value in self.config.items(session_name)} 

    def load_config(self, group_id: int, group_title: str) -> dict:
        # Check if the config file and the sessions exists
        try:
            self.config.read(self.config_file)
            if not self.config.has_section(str(group_id)):
                self._create_new_conf(group_id, group_title)
                print(f"Saved a new entry {group_id} to file {self.config_file}.")

            return self._get_session(str(group_id))
        
        # It doesn't exist or it's bad configured, creating a new one
        except (FileNotFoundError, ValueError) as e:
            print("File not found or bad formated error: {e}")
            print("Creating a new one")
            self._create_new_conf(group_id, group_title)
            return self._get_session(str(group_id))


