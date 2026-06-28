import logging

from myglobal import *


def step2_process(llm_name):
    logging.info(f'Step 2: collecting expenses values with LLM = {llm_name}')

    target_config = None
    for config in llm_configs:
        llm = config['name']
        if llm == llm_name:
            target_config = config
            break

    if target_config is None:
        logging.error(f'LLM {llm_name} not found')
        return

    # step 2 - add sum
    for i in target_industries:

        industry_name = industries[i]
        expenses = load_file(f'{i}_expense_list.md')

        for r in target_regions:
            result_filename = f'{i}_{r}_{llm_name}_expense_sum.md'
            if Path(CONFIG['data']['output'] + '/' + result_filename).is_file():
                logging.debug(f'The file {result_filename} exists, skipping.')
                continue

            try:
                region_name = regions[r]
            except:
                logging.warning(f'Not found: region_id={r}')
                continue

            inv_dict = segm_by_reg_ind.get((r, i))
            if inv_dict is None:
                logging.error(f'Not found: industry_id={i} region_id={r}')
                continue

            budget_s = inv_dict.get('S')
            budget_m = inv_dict.get('M')
            budget_l = inv_dict.get('L')
            prompt = load_prompt('02-add-sum-v2.txt', {
                'industry_name': industry_name,
                'region_name': region_name,
                'list': expenses,
                'budget_s': str(budget_s),
                'budget_m': str(budget_m),
                'budget_l': str(budget_l),
            })
            # добавляем суммы
            logging.info(f'Step 2: industry_id={i}, region_id={r}, llm={llm_name}')

            # получаем ответ от LLM на наш промпт
            expenses_with_sum = ask_llm(target_config, prompt) + '\n'
            logging.info(expenses_with_sum)
            save_file(result_filename, expenses_with_sum)


def get_investment(segments_list, regions_dict, industries_dict):
    result = dict([])
    for seg in segments_list:
        r = seg['region_id']
        i = seg['industry_id']
        s = seg['size']
        if r in regions_dict and i in industries_dict:
            v = result.setdefault((r, i), dict([]))
            v[s] = seg['investment']
    return result


target_regions = list(regions.keys())[:]
target_industries = list(industries.keys())[:]

segm_by_reg_ind = get_investment(segments, target_regions, target_industries)
logging.debug(f'investments by (region, industry) = {segm_by_reg_ind}')
