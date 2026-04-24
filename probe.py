import base64
import json
import time
import uuid
from pathlib import Path

import requests
from envyaml import EnvYAML
from gigachat import GigaChat

CONFIG = EnvYAML('config.yaml')
TOKEN_FILE_NAME = 'token.json'
LOGS_DIR = 'logs'


def main():
    init_logs()
    load_config()

    giga = GigaChat(
        access_token=get_token()['access_token']
    )

    # название файла без расширения с промптом
    prompt_name = 'costs_v04'
    # в дальнейшем параметры для prompt будем брать из CSV по всем отраслям
    prompt = load_prompt(prompt_name, {
        'industry_group': 'Розничная торговля',
        'industry_name': 'Цветы и подарки',
        'region_name': 'Москва',
        # в зависимости от указанного бюджета ориентируемся Q1/Q2/Q3 из CSV
        'budget': '200000'
    })

    ask_giga(giga, prompt)


def init_logs():
    Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)


def save_log(log, sfx):
    tm = time.time_ns()
    with open(f'{LOGS_DIR}/{tm}_{sfx}.txt', 'w', encoding='utf-8') as f:
        f.write(str(log))


def ask_giga(giga, prompt):
    save_log(prompt, 'req')
    response = giga.chat(prompt)
    save_log(response, 'resp')
    print(response.choices[0].message.content)


def load_prompt(prompt_name, params):
    with open('prompts/' + prompt_name + '.txt', 'r', encoding='utf-8') as f:
        data = f.read()
    for key, value in params.items():
        data = data.replace('{' + key + '}', value)
    return data


def load_config():
    # Load and parse the file automatically substituting env variables
    active_llm = CONFIG['llms']['active']
    if active_llm != 'gigachat':
        print(f'The version \'{active_llm}\' is not supported as LLM API')
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
    print(f'token = {token}')
    return token


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
