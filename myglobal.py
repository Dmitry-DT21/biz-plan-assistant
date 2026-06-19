import base64
import csv
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, date
from pathlib import Path

import requests
from envyaml import EnvYAML
from gigachat import GigaChat
from openai import OpenAI

CONFIG = EnvYAML('config.yaml')
PROMPTS_PATH = CONFIG['prompts']['path']
LOGS_LLM_PATH = CONFIG['logs']['path']['llm']
LOGS_OUTPUT_PATH = CONFIG['logs']['path']['output']
OUTPUT_FILE = CONFIG['data']['output'] + '/' + datetime.now().strftime('%Y%m%d') + '.csv'
INDUSTRIES_FILE = CONFIG['data']['industries']
REGIONS_FILE = CONFIG['data']['regions']
SEGMENTS_FILE = CONFIG['data']['segments']
TOKEN_FILE_NAME = 'token.json'


# создаем директорию для логов
def init_logs():
    Path(LOGS_LLM_PATH).mkdir(parents=True, exist_ok=True)
    # default log level
    level = logging.ERROR
    match CONFIG['logs']['level']:
        case 'DEBUG':
            level = logging.DEBUG
        case 'INFO':
            level = logging.INFO
        case 'WARN':
            level = logging.WARN
    Path(LOGS_OUTPUT_PATH).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(f'{LOGS_OUTPUT_PATH}/{date.today():%Y%m%d}.log'),  # Logs to a file
            logging.StreamHandler(sys.stdout)  # Logs to the console
        ]
    )


def load_industries():
    industries = {}
    logging.info(f'Читаем файл со списком отраслей/индустрий {INDUSTRIES_FILE}')
    with open(INDUSTRIES_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:
            industries[int(row['industry_id'])] = row['industry_name']
    logging.debug(f'industries: {industries}')
    return industries


def load_regions():
    regions = {}
    logging.info(f'Читаем файл со списком регионов {REGIONS_FILE}')
    with open(REGIONS_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:
            regions[int(row['region_id'])] = row['region_name']
    logging.debug(f'regions: {regions}')
    return regions


def load_segments():
    result = []
    logging.info(f'Читаем файл со списком инвестиций/сегментов {SEGMENTS_FILE}')
    with open(SEGMENTS_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=';')
        for row in reader:
            result.append({
                'industry_id': int(row['industry_id']),
                'region_id': int(row['region_id']),
                'size': row['size_of_business'],
                'investment': int(row['initial_investment'])
            })
    logging.debug(f'segments: {result}')
    return result


# unused?
def filter_segments(segments):
    # фильтруем сегменты по доступным регионам и отраслям
    filtered = []
    for segment in segments:
        if segment['industry_id'] not in industries:
            continue
        if segment['region_id'] not in regions:
            continue
        filtered.append(segment)
    return filtered


# создаем директорию для сохранения результата работы
def init_output():
    Path(CONFIG['data']['output']).mkdir(parents=True, exist_ok=True)


# загружает конфигурацию из config.yaml, создаем клиента для выбранной LLM
def load_llm_config():
    logging.info('Загружаем конфигурацию по поддерживаемым LLM')
    result = []
    for config in CONFIG['LLM']['config']:
        name = config['name']
        enabled = bool(config['enabled'])
        logging.info(f'LLM name={name}, enabled={enabled}')
        if not enabled:
            continue
        client = None
        if enabled:
            match name:
                case 'openai' | 'deepseek':
                    client = OpenAI(
                        api_key=config['api-key'],
                        base_url=config['api']
                    )
                case 'gigachat':
                    client = initGiga(config)
                case _:
                    print(f'LLM {name} не поддерживается')
                    exit(1)
            config['client'] = client
        result.append(config)
    return result


def initGiga(config):
    token = get_token(config)['access_token']
    return GigaChat(
        access_token=token,
        base_url=config['api'],
        model=config['model']
    )


# GigaChat: получение access_token
# если токен протух, то заново выполняем аутентификацию
def get_token(config):
    token = dict([])
    try:
        with open('token.json', 'r', encoding='utf-8') as f:
            token = json.load(f)
            if token_expired(token):
                raise Exception('Token expired')
            token['cached'] = True
    except Exception as e:
        logging.warning(e)
        token = authenticate(config)
    logging.debug(f'token = {token}')
    return token


def token_expired(token):
    expires_at = token['expires_at']
    # ns -> ms and 3 seconds for reserve
    return True if time.time() * 1_000 >= expires_at - 3_000 else False


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


# добавляем строку с данными в выходной файл результата
def append_output(data):
    if not os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('industry_id;region_id;industry;region;size;expense;amount;min;max\n')

    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(f'{data['industry_id']};{data['region_id']};{data['industry']};{data['region']};{data['size']};"{data['expense']}";{data['amount']};{data['min']};{data['max']}\n')


# сохранение строки в папке для логов
# название файла - временная метка плюс суффикс для идентификации запрос/ответ
def save_log(log, model, sfx):
    tm = f"{datetime.now():%Y%m%d-%H%M%S%f}"
    with open(f'{LOGS_LLM_PATH}/{tm}_{model}_{sfx}.txt', 'w', encoding='utf-8') as f:
        f.write(str(log))


# загружаем промпт с подстановкой параметров
def load_prompt(prompt_name, params):
    with open(f'{PROMPTS_PATH}/{prompt_name}', 'r', encoding='utf-8') as f:
        data = f.read()
        for key, value in params.items():
            data = data.replace('{' + key + '}', value)
        return data


# основной метод запроса данных у LLM, используем конфиг для определения конкретного варианта сервиса
# запрос и ответ логируем
def ask_llm(config, prompt):
    model = config['model']
    save_log(prompt, model, 'req')
    client = config['client']
    response = None

    match config['name']:
        case 'gigachat':
            try:
                response = client.chat(prompt)
            except Exception:
                # 401
                client = initGiga(config)
                config['client'] = client
                response = client.chat(prompt)
        case 'deepseek':
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                stream=False,
                # reasoning_effort="high",
                extra_body={"thinking": {"type": "disabled"}}
            )
        case 'openai':
            response = client.responses.create(
                model=model,
                input=prompt
            )

    save_log(response, model, 'resp')
    answer = response.output_text if config['name'] == 'openai' else response.choices[0].message.content
    # logging.debug(answer)
    return answer


init_logs()
init_output()
llm_configs = load_llm_config()
industries = load_industries()
regions = load_regions()
segments = load_segments()
# filtered_segments = filter_segments(segments)
logging.info('myglobal module initialized')
