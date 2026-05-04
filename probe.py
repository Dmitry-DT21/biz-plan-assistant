import base64
import csv
import json
import logging
import time
import uuid
from pathlib import Path

import requests
from envyaml import EnvYAML
from gigachat import GigaChat
from openai import OpenAI

CONFIG = EnvYAML('config.yaml')  # Load and parse the file automatically substituting env variables
PROMPTS_PATH = CONFIG['prompts']['path']
LOGS_PATH = CONFIG['logs']['path']
INDUSTRIES_FILE = CONFIG['data']['industries']
REGIONS_FILE = CONFIG['data']['regions']
SEGMENTS_FILE = CONFIG['data']['segments']
TOKEN_FILE_NAME = 'token.json'


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    init_logs()
    llm_configs = load_llm_config()

    industries = load_industries()
    regions = load_regions()
    segments = load_segments()

    # фильтруем сегменты по доступным регионам и отраслям
    filtered_segments = []
    for segment in segments:
        if segment['industry_id'] not in industries:
            continue
        if segment['region_id'] not in regions:
            continue
        filtered_segments.append(segment)
    logging.info(f'Исходный список {len(segments)}, отфильтрованный {len(filtered_segments)}')

    # основной цикл
    for segment in filtered_segments:
        industry_id = segment['industry_id']
        region_id = segment['region_id']
        size = segment['size']
        investment = segment['investment']

        # 1) сначала получаем N списков статей расходов по нескольким LLM
        prompt = load_prompt('expenses.txt', {
            'industry_name': industries[industry_id],
            'region_name': regions[region_id],
            'budget': str(investment)
        })

        expenses = ''
        for config in llm_configs:
            # получаем ответ от LLM на наш промпт
            expenses = expenses + '\n' + ask_llm(config, prompt) + '\n'
        logging.info(f'Все статьи расходов от всех LLM {expenses}')

        # 2) из всех списков формируем один
        prompt = load_prompt('expenses-merge.txt', {
            'industry_name': industries[industry_id],
            'list': expenses
        })
        # просим объединить статьи у одной LLM (любая должна справиться)
        merged_expenses = ask_llm(llm_configs[0], prompt)

        # 3) получаем суммы по статьям расходов
        prompt = load_prompt('expenses-sum.txt', {
            'industry_name': industries[industry_id],
            'region_name': regions[region_id],
            'budget': str(investment),
            'list': merged_expenses
        })
        # todo remove next line
        break


def load_industries():
    industries = {}
    logging.info(f'Читаем файл со списком отраслей/индустрий {INDUSTRIES_FILE}')
    with open(INDUSTRIES_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=',')
        for row in reader:
            industries[int(row['industry_id'])] = row['industry_name']
    logging.debug(f'industries: {industries}')
    return industries


def load_regions():
    regions = {}
    logging.info(f'Читаем файл со списком регионов {REGIONS_FILE}')
    with open(REGIONS_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=',')
        for row in reader:
            regions[int(row['region_id'])] = row['region_name']
    logging.debug(f'regions: {regions}')
    return regions


def load_segments():
    segments = []
    logging.info(f'Читаем файл со списком инвестиций/сегментов {SEGMENTS_FILE}')
    with open(SEGMENTS_FILE, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file, delimiter=',')
        for row in reader:
            segments.append({
                'industry_id': int(row['industry_id']),
                'region_id': int(row['region_id']),
                'size': row['sizeofbusiness'],
                'investment': int(row['initialinvestment'])
            })
    logging.debug(f'segments: {segments}')
    return segments


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
def ask_llm(config, prompt):
    model = config['model']
    save_log(prompt, model, 'req')
    client = config['client']
    response = None

    match config['name']:
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
    answer = response.output_text if config['name'] == 'openai' else response.choices[0].message.content
    logging.info(answer)
    return answer


# загружаем промпт с подстановкой параметров
def load_prompt(prompt_name, params):
    with open(f'{PROMPTS_PATH}/{prompt_name}', 'r', encoding='utf-8') as f:
        data = f.read()
        for key, value in params.items():
            data = data.replace('{' + key + '}', value)
        return data


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
                    client = GigaChat(
                        access_token=get_token()['access_token'],
                        base_url=config['api'],
                        model=config['model']
                    )
                case _:
                    print(f'LLM {name} не поддерживается')
                    exit(1)
            config['client'] = client
        result.append(config)
    return result


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
        logging.warning(e)
        token = authenticate(CONFIG['llms']['configs']['gigachat'])
    logging.debug(f'token = {token}')
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
