from myglobal import *


def main():
    offset = 0
    limit = 3
    logging.info(f'Исходный список {len(segments)}, отфильтрованный по сегментам и регионам {len(filtered_segments)}')

    # основной цикл
    n = 0
    for segment in filtered_segments[offset:offset + limit]:
        industry_id = segment['industry_id']
        region_id = segment['region_id']
        size = segment['size']
        investment = segment['investment']
        logging.info(
            f'industry={industries[industry_id]},{industry_id}, region={regions[region_id]},{region_id}, size={size}, investment={investment}, offset={offset}, n={n}')
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
    merged_expenses = ask_llm(llm_configs[2], prompt)
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
        amount = to_number(values[1])
        if amount is None:
            continue
        min = to_number(values[2])
        max = to_number(values[3])
        append_output({
            'industry_id': industry_id,
            'region_id': region_id,
            'industry': industries[industry_id],
            'region': regions[region_id],
            'size': investment_size,
            'expense': expense_name,
            'amount': amount,
            'min': min,
            'max': max,
        })


def to_number(s):
    try:
        return int(s.replace(' ', ''))
    except:
        return None


if __name__ == "__main__":
    main()
