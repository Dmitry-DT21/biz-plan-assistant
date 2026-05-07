import base64
import csv
import json
import logging
import sys
import time
import uuid
from datetime import datetime, date
from pathlib import Path

import requests
from envyaml import EnvYAML
from gigachat import GigaChat
from openai import OpenAI

CONFIG = EnvYAML('config.yaml')  # Load and parse the file automatically substituting env variables
PROMPTS_PATH = CONFIG['prompts']['path']
LOGS_PATH = CONFIG['logs']['path']
LOGS_OUTPUT_PATH = CONFIG['logs']['output_path']
OUTPUT_FILE = CONFIG['data']['output'] + '/' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.csv'
INDUSTRIES_FILE = CONFIG['data']['industries']
REGIONS_FILE = CONFIG['data']['regions']
SEGMENTS_FILE = CONFIG['data']['segments']
TOKEN_FILE_NAME = 'token.json'


def main():
    init_logs()
    init_output()
    llm_configs = load_llm_config()

    industries = load_industries()
    regions = load_regions()
    segments = load_segments()

    # tups50 = set()
    # фильтруем сегменты по доступным регионам и отраслям
    filtered_segments = []
    for segment in segments:
        if segment['industry_id'] not in industries:
            continue
        if segment['region_id'] not in regions:
            continue
        filtered_segments.append(segment)
        # tups50.add((int(segment['industry_id']), int(segment['region_id']), segment['size']))
        # if len(tups50) == 50:
        #     break

    # tups = set()
    # with open('output/result-50.csv', mode='r', encoding='utf-8') as file:
    #     reader = csv.DictReader(file, delimiter=',')
    #     for row in reader:
    #         tups.add((int(row['industry_id']), int(row['region_id']), row['size']))
    #
    # print(tups50 - tups)
    # (401, 6101, 'M'), (3, 3401, 'M'), (105, 6601, 'S'), (401, 2401, 'S')
    # filtered_segments = [
    #     {
    #         "industry_id": 401,
    #         "region_id": 6101,
    #         "size": 'M',
    #         "investment": 19965000
    #     },
    #     {
    #         "industry_id": 3,
    #         "region_id": 3401,
    #         "size": 'M',
    #         "investment": 1080000
    #     },
    #     {
    #         "industry_id": 105,
    #         "region_id": 6601,
    #         "size": 'S',
    #         "investment": 575000
    #     },
    #     {
    #         "industry_id": 401,
    #         "region_id": 2401,
    #         "size": 'S',
    #         "investment": 6760000
    #     }
    #     ]
    #     # (401, 6101, 'M'), (3, 3401, 'M'), (105, 6601, 'S'), (401, 2401, 'S')]

    offset = 50
    limit = 1
    logging.info(f'Исходный список {len(segments)}, отфильтрованный по сегментам и регионам {len(filtered_segments)}')

    # основной цикл
    n = 0
    for segment in filtered_segments[offset:offset + limit]:
        industry_id = segment['industry_id']
        region_id = segment['region_id']
        size = segment['size']
        investment = segment['investment']
        logging.info(
            f'industry_id={industry_id}, region_id={region_id}, size={size}, investment={investment}, offset={offset}, n={n}')
        n += 1

        # 1) сначала получаем список статей затрат по каждой LLM
        expenses = step1_init(llm_configs, industries[industry_id], regions[region_id], str(investment))

        # 2) из всех списков формируем один
        merged_expenses = step2_merge(llm_configs, regions[region_id], expenses)

        # 3) добавляем суммы по статьям затрат
        expenses_with_sum = step3_sum(llm_configs, industries[industry_id], regions[region_id], investment,
                                      merged_expenses)

        # 4) считаем средние затраты по объединенному списку у одной LLM
        avg_expenses = step4(llm_configs, expenses_with_sum)

        # 5) сохраняем результат
        step5_result(industry_id, region_id, size, avg_expenses)

    logging.info(f'count={n}')


def step1_init(llm_configs, industry, region, investment):
    prompt = load_prompt('01-init.txt', {
        'industry_name': industry,
        'region_name': region,
        'budget': investment
    })
    expenses = ''
    for config in llm_configs:
        # получаем ответ от LLM на наш промпт
        expenses = expenses + '\n' + ask_llm(config, prompt) + '\n'
    logging.info(f'"Этап 1: Все статьи затрат от всех LLM\n{expenses}')
    return expenses


def step2_merge(llm_configs, industry, expenses):
    prompt = load_prompt('02-merge-lists.txt', {
        'industry_name': industry,
        'list': expenses
    })
    # объединяем статьи (используем одну LLM, любая должна справиться)
    merged_expenses = ask_llm(llm_configs[0], prompt)
    logging.info(f'Этап 2: Объединенный список затрат (по нему будем собирать суммы)\n{merged_expenses}')
    return merged_expenses


def step3_sum(llm_configs, industry, region, investment, merged_expenses):
    prompt = load_prompt('03-add-sum.txt', {
        'industry_name': industry,
        'region_name': region,
        'budget': str(investment),
        'list': merged_expenses
    })
    expenses_with_sum = ''
    for config in llm_configs:
        # получаем ответ от LLM на наш промпт
        expenses_with_sum = expenses_with_sum + '\n' + ask_llm(config, prompt) + '\n'
    logging.info(f'Этап 3: Добавляем сумму затрат\n{expenses_with_sum}')
    return expenses_with_sum


def step4(llm_configs, expenses_with_sum):
    prompt = load_prompt('04-avg.txt', {
        'list': expenses_with_sum
    })
    avg_expenses = ask_llm(llm_configs[0], prompt)
    logging.info(f'Этап 4: Объединенный список затрат со средними суммами\n{avg_expenses}')
    return avg_expenses


def step5_result(industry_id, region_id, investment_size, avg_expenses):
    for s in avg_expenses.split('\n'):
        if s == '':
            continue
        row = s.split('|')
        values = []
        for v in row:
            if v == '':
                continue
            values.append(v)
        if len(values) < 2:
            logging.warning(f'skip industry_id={industry_id}, region_id={region_id}, investment_size={investment_size}')
            continue
        expense_name = values[0].strip()
        try:
            sum = int(values[1].replace(' ', ''))
        except ValueError:
            continue
        append_output({
            'industry_id': industry_id,
            'region_id': region_id,
            'size': investment_size,
            'expense': expense_name,
            'amount': sum,
        })


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


# создаем директорию для сохранения результата работы
def init_output():
    Path(CONFIG['data']['output']).mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('region_id,industry_id,size,expense,amount\n')


# добавляем строку с данными в выходной файл результата
def append_output(data):
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(f'{data['region_id']},{data['industry_id']},{data['size']},"{data['expense']}",{data['amount']}\n')


# сохранение строки в папке для логов
# название файла - временная метка плюс суффикс для идентификации запрос/ответ
def save_log(log, model, sfx):
    tm = f"{datetime.now():%Y%m%d-%H%M%S%f}"
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
                # extra_body={"thinking": {"type": "enabled"}}
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


if __name__ == "__main__":
    main()
#     init_output()
#     step5_result(1, 6101, 'L','''
# Аренда и депозит | 716667
# Ремонт и отделка помещения | 1533333
# Торговый, холодильный и кассовое оборудование | 2900000
# Охрана и видеонаблюдение | 273333
# Первичная закупка товаров | 2100000
# Позиционирование: вывески, наружная реклама, POS-материалы | 483333
# Лицензирование и разрешительные документы | 123333
# Программное обеспечение и кассовые системы | 196667
# Запуск бизнеса: реклама и продвижение | 516667
# Оборотный капитал и резервный фонд | 1253333
# Франшиза/паушальный взнос | 243333
# ''')

#     step5_result(702, 2401, 'M', '''
# Аренда помещения и обеспечительный платеж | 75000
# Ремонт и оформление офиса/точки | 85000
# Закупка инструментов, оборудования и мебели | 126667
# Первичные запасы расходных материалов и демонстрационные образцы | 36667
# Маркетинг, реклама и продвижение | 40000
# Сайт, CRM, телефония и программное обеспечение | 18333
# Лицензионные платежи и регистрация бизнеса | 10000
# Оплата первичного фонда зарплаты сотрудникам | 76667
# Обучение сотрудников и аттестационные мероприятия | 11667
# Транспортные и сопутствующие операционные расходы | 13333
# Паушальный взнос по франшизе (при наличии) | 51667
# ''')