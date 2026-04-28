import base64
import json
import time
import uuid
import csv
from pathlib import Path

import requests
from envyaml import EnvYAML
from gigachat import GigaChat
from openai import OpenAI

CONFIG = EnvYAML('config.yaml')  # Load and parse the file automatically substituting env variables
PROMPTS_PATH = CONFIG['prompts']['path']
LOGS_PATH = CONFIG['logs']['path']
IDEA_FILE = CONFIG['idea']['file']
TOKEN_FILE_NAME = 'token.json'


def main():
    init_logs()
    load_config()

    print('MAIN: читаем файл с бизнес-идеями')
    with open(IDEA_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:
            print('-' * 80)
            print(f'IDEA: idea=<{row['idea']}>, region=<{row['region']}>, budget=<{row['budget']}>')
            prompt = load_prompt('costs.txt', {
                'idea': row['idea'],
                'region_name': row['region'],
                'budget': row['budget']
            })
            print('PROMPT:')
            print(prompt)
            print('-' * 80)
            for llm, config in CONFIG['llms']['configs'].items():
                # пропускаем неактивные LLM
                if not config['enabled']:
                    continue
                client = config['client']
                print(f'INFO: LLM={llm} model={config['model']}')
                print('ANSWER:')
                # получаем ответ от LLM на наш промпт
                ask_llm(llm, config, prompt)
                print('-' * 80)


# создаем директорию для логов
def init_logs():
    Path(LOGS_PATH).mkdir(parents=True, exist_ok=True)


# сохранение строки в папке для логов
# название файла - временная метка плюс суффикс для идентификации запрос/ответ
def save_log(log, model, sfx):
    tm = time.time_ns()
    with open(f'{LOGS_PATH}/{tm}_{model}_{sfx}.txt', 'w', encoding='utf-8') as f:
        f.write(str(log))


# основной метод запроса данных у LLM, используем конфиг для определения конкретного варианта сервиса
# запрос и ответ логируем
def ask_llm(llm_name, config, prompt):
    model = config['model']
    save_log(prompt, model, 'req')
    client = config['client']
    response = None

    match llm_name:
        case 'gigachat':
            response = client.chat(prompt)
        case 'deepseek':
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                stream=False,
                reasoning_effort="high",
                extra_body={"thinking": {"type": "enabled"}}
            )
        case 'openai':
            response = client.responses.create(
                model=model,
                input=prompt
            )

    save_log(response, model, 'resp')
    if llm_name == 'openai':
        print(response.output_text)
    else:
        print(response.choices[0].message.content)


# загружаем промпт с подстановкой параметров
def load_prompt(prompt_name, params):
    with open(f'{PROMPTS_PATH}/{prompt_name}', 'r', encoding='utf-8') as f:
        data = f.read()
        for key, value in params.items():
            data = data.replace('{' + key + '}', value)
        return data


# загружает конфигурацию из config.yaml, создаем клиента для выбранной LLM
def load_config():
    print('CONFIG: загружаем конфигурацию по поддерживаемым LLM')
    for llm, config in CONFIG['llms']['configs'].items():
        enabled = bool(config['enabled'])
        client = None
        if enabled:
            match llm:
                case 'openai' | 'deepseek':
                    client = OpenAI(
                        api_key=config['api-key'],
                        base_url=config['api']
                    )
                case 'gigachat':
                    client = GigaChat(
                        access_token=get_token()['access_token'],
                        base_url=config['api'],
                        model=config['model']
                    )
                case _:
                    print(f'LLM {llm} не поддерживается')
                    exit(1)
            config['client'] = client


# GigaChat: получение access_token
# если токен протух, то заново выполняем аутентификацию
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


# GigaChat: аутентификация и получение access_token
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
