import os
import typer
from loguru import logger
import streamlit_authenticator as stauth
import yaml

app = typer.Typer()

parent_dir = os.curdir
directories = os.listdir()
path_dotfile = f'{parent_dir}/.env'
path_yamlfile = f'{parent_dir}/config.yaml'

def check_dotenv():
    
    if '.env' in directories:
        return True
    else:
        return False

def create_env():
    
    if not check_dotenv():
        
        with open(path_dotfile, mode='w') as f:
            f.write('')

def add_entries(model: str):
    """
    add basic required environment variables based on the choice of model made. 

    :param model: The name of the LLM. One of the models mentioned in the PydanticAI documentation.
    :type model: str
    """
    
    if os.getenv("GPT-MODEL-NAME") == None:
        model_name = model
    else:
        model_name = os.getenv("GPT-MODEL-NAME")

    if 'gpt' in model_name:
        
        with open(path_dotfile, mode='w') as f:
            api_key = input(f'Enter your {model_name} API key')
            f.write(f"""OPENAI_API_KEY={api_key}
GPT-MODEL-NAME={model}""")

    elif 'gemini' in model_name:

        with open(path_dotfile, mode='w') as f:
            api_key = input(f'Enter your {model_name} API key')
            f.write(f"""GEMINI_API_KEY={api_key}
GPT-MODEL-NAME={model}""")

def setup_config():

    if 'config.yaml' not in directories:
        username = input('pick your username for login: ')
        email = input('insert your email: ')
        name = input('insert your name: ')
        password = input('select your password for logins: ')
        cookie_name = input('pick cookie name: ')
        cookie_key = input('pick your cookie key: ')
        expiry_days = input('set after how many days the cookie will expire: ')

        hashed_password = stauth.Hasher.hash_list([password])
        cleaned_pass = hashed_password[0]
        
        write_dct = {
            'credentials' : {
                'usernames' : {
                username : {
                    'email' : email,
                    'name' : name,
                    'password' : cleaned_pass}}},
                    
            'cookie' : {
                'name' : cookie_name,
                'key' : cookie_key,
                'expiry_days' : expiry_days
            }}

        with open(path_yamlfile, mode='w') as f:

            yaml.dump(write_dct, f, default_flow_style=False)

@app.command()
def main():
    # creating .env file if it does not already exists
    logger.info("Checking if .env file already exists")
    if not check_dotenv():
        logger.info("Creating .env file in project directory")
        create_env()
        logger.info("Adding required environment variables now...")

        #! make this dropdown menu
        model = input('name of the model (e.g.; google-gla:gemini-2.0-flash, gpt-4o): ')

        add_entries(model=model)

        logger.success(".env file correctly created")

    else:
        logger.success(".env file already exists!")

    
    # creating yaml file if it does not already exist
    if 'config.yaml' not in directories:
        logger.info('Starting configuration of config.yaml file...')
        setup_config()
        logger.success('config.yaml correctly created')
    else:
        logger.success('config.yaml already exists!')

if __name__ == "__main__":
    app()


