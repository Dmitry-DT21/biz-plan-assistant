import base64
import json
import time
import uuid
from pathlib import Path

import requests
from envyaml import EnvYAML
from gigachat import GigaChat
from openai import OpenAI

CONFIG = EnvYAML('config.yaml')
TOKEN_FILE_NAME = 'token.json'
LOGS_DIR = 'logs'


def main():
    init_logs()
    config = load_config()
    # название файла без расширения с промптом
    prompt_name = 'costs'
    # в дальнейшем параметры для prompt будем брать из CSV по всем отраслям
    prompt = load_prompt(config, prompt_name, {
        'industry_group': 'Розничная торговля',
        'industry_name': 'Цветы и подарки',
        'region_name': 'Москва',
        # в зависимости от указанного бюджета ориентируемся Q1/Q2/Q3 из CSV
        'budget': '200000'
    })

    ask_llm(config, prompt)


# создаем директорию для логов
def init_logs():
    Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)


# сохранение строки в папке для логов
# название файла - временная метка плюс суффикс для идентификации запрос/ответ
def save_log(log, model, sfx):
    tm = time.time_ns()
    with open(f'{LOGS_DIR}/{tm}_{model}_{sfx}.txt', 'w', encoding='utf-8') as f:
        f.write(str(log))


# основной метод запроса данных у LLM, используем конфиг для определения конкретного варианта сервиса
# запрос и ответ логируем
def ask_llm(config, prompt):
    model = config['model']
    save_log(prompt, model, 'req')
    response = ''
    if config['llm'] == 'gigachat':
        giga = config['giga']
        response = giga.chat(prompt)
    elif config['llm'] == 'deepseek':
        client = config['client']
        response = client.chat.completions.create(
            model=model,
            messages=[
                # {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": prompt},
            ],
            stream=False,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}}
        )
    elif config['llm'] == 'openai':
        client = config['client']
        response = client.responses.create(
            model=model,
            input=prompt
        )
    save_log(response, model, 'resp')
    if config['llm'] == 'openai':
        print(response.output_text)
    else:
        print(response.choices[0].message.content)


# загружаем промпт в зависимости от выбранной LLM (для разных LLM промпты могут различаться)
def load_prompt(config, prompt_name, params):
    prompt_dir = config['prompt_dir']
    with open(f'{prompt_dir}/{prompt_name}.txt', 'r', encoding='utf-8') as f:
        data = f.read()
        for key, value in params.items():
            data = data.replace('{' + key + '}', value)
        return data


# загружает конфигурацию из config.yaml, создаем клиента для выбранной LLM
def load_config():
    # Load and parse the file automatically substituting env variables
    active_llm = CONFIG['llms']['active']
    config = CONFIG['llms']['configs'][active_llm]
    if active_llm in ['openai', 'deepseek']:
        model = config['model']
        client = OpenAI(
            api_key=config['api-key'],
            base_url=config['api']
        )
        return {'llm': active_llm, 'prompt_dir': 'prompts/' + active_llm, 'client': client, 'model': model}
    if active_llm == 'deepseek':
        model = config['model']
        client = OpenAI(
            api_key=config['api-key'],
            base_url=config['api']
        )
        return {'llm': active_llm, 'prompt_dir': 'prompts/' + active_llm, 'client': client, 'model': model}
    if active_llm == 'gigachat':
        giga = GigaChat(
            access_token=get_token()['access_token'],
            base_url=config['api'],
            model=config['model']
        )
        return {'llm': active_llm, 'prompt_dir': 'prompts/' + active_llm, 'giga': giga}
    print(f'The version \'{active_llm}\' is not supported as LLM API')
    exit(1)


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
