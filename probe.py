from myglobal import *


def main():
    offset = 53
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
            amount = int(values[1].replace(' ', ''))
        except ValueError:
            continue
        append_output({
            'industry_id': industry_id,
            'region_id': region_id,
            'size': investment_size,
            'expense': expense_name,
            'amount': amount,
        })


if __name__ == "__main__":
    main()
#     init_logs()
#     init_output()
#     llm_configs = load_llm_config()
#     prompt = load_prompt('04-critics1.txt', {
#         'industry_name': 'Услуги по ремонту автомобилей',
#         'region_name': 'Уфа',
#         'budget': '400000',
#         'list': '''
# | Статья затрат              | Средняя сумма |
# |---------------------------|---------------|
# | Аренда и ремонт помещения | 120000        |
# | Оборудование и инструмент  | 100000        |
# | Запчасти и расходники      | 47500         |
# | Организация клиентской зоны| 22500         |
# | Зарплаты сотрудников       | 47500         |
# | Маркетинг и реклама        | 22500         |
# | Разрешительные документы   | 11500         |
# | Общие коммунальные расходы| 10500         |
# | Страховка                  | 6500          |
# | Юридические консультации   | 11500         |
# '''
#     })
#     answer = ask_llm(llm_configs[1], prompt)
#     logging.info(answer)

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
