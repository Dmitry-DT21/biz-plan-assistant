import logging

from myglobal import *


def main():
    segment_investment = {}
    for segment in filtered_segments:
        segment_investment[(segment['industry_id'], segment['region_id'], segment['size'])] = int(segment['investment'])
    logging.debug(segment_investment)

    investments = {}
    expenses = {}
    tups = set()
    expenses_file = 'output/result-3-ex.csv'
    with open(expenses_file, 'r') as f:
        reader = csv.DictReader(f, delimiter=',')
        for r in reader:
            tup = (int(r['industry_id']), int(r['region_id']), r['size'])
            tups.add(tup)
            investment = segment_investment[tup]
            investments[tup] = investment
            expenses.setdefault(tup, '| Статья затрат | Сумма |\n|---|---|')
            expenses[tup] = f'{expenses[tup]}\n|{r['expense']}|{r['amount']}|'
    logging.debug(f'investments={investments}')
    logging.debug(f'expenses={expenses}')

    for tup in tups:
        investment = investments[tup]
        expense_list = expenses[tup]
        industry = industries[tup[0]]
        region = regions[tup[1]]
        size = tup[2]
        budget = str(investment)
        prompt = load_prompt('04-critics.txt', {
            'industry_name': industry,
            'region_name': region,
            'budget': budget,
            'list': expense_list
        })
        logging.debug(prompt)
        answer = ask_llm(llm_configs[2], prompt)
        logging.info(f'{industry}, {region}, {size}, {budget}\n')
        logging.info(answer)


if __name__ == "__main__":
    main()
