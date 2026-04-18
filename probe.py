from envyaml import EnvYAML
from gigachat import GigaChat
import time
import requests
import uuid
import base64
import json

CONFIG = EnvYAML('config.yaml')


def main():
    load_config()
    token = get_token()
    print(f'token = {token}')

    giga = GigaChat(
        access_token=token['access_token']
    )
    print(f'giga = {giga}')

    response = giga.chat("Привет! Как дела?")
    print(response.choices[0].message.content)


def load_config():
    # Load and parse the file automatically substituting env variables
    active_llm = CONFIG['llms']['active']
    if active_llm != 'gigachat':
        print(f'The version \'{active_llm}\' does not support as LLM API')
        exit(1)


def get_token():
    token = dict([])
    try:
        with open('token.json', 'r', encoding='utf-8') as f:
            token = json.load(f)
            expires_at = token['expires_at']
            if time.time() * 1_000 >= expires_at - 3_000:
                raise Exception('Token expired')
            token['cached'] = True
    except Exception as e:
        print(f'WARN: {e}')
        token = authenticate(CONFIG['llms']['configs']['gigachat'])
    return token


TOKEN_FILE_NAME = 'token.json'


def authenticate(config):
    client_id = config['client-id']
    client_secret = config['client-secret']
    auth_key_bytes = base64.b64encode((client_id + ':' + client_secret).encode('utf-8'))
    auth_key = auth_key_bytes.decode('utf-8')
    url = config['auth']
    payload = {
        'scope': 'GIGACHAT_API_PERS'
    }
    req_id = uuid.uuid4()
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(req_id),
        'Authorization': 'Basic ' + auth_key
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    save_token_to_file(response.text)
    return response.json()


def save_token_to_file(s):
    with open(TOKEN_FILE_NAME, "w") as f:
        f.write(s)


if __name__ == "__main__":
    main()
