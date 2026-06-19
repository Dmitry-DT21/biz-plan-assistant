from myglobal import *


def main():
    logging.info("Generating expenses v2")
    target_regions = [10, 23, 50, 77, 78, 2301, 3601, 5201, 5401, 5501]
    # target_industries = [20206, 50303, 60303, 90102, 90109, 100101, 131301, 140607, 150202, 181801]
    # target_regions = [5401]
    target_industries = [20206]

    segm_by_reg_ind = get_investment(segments, target_regions, target_industries)
    logging.debug(f'investments by (region, industry) = {segm_by_reg_ind}')

    # # step 1 - get expenses list by every industry
    # for i in target_industries:
    #     industry_name = industries[i]
    #     logging.info(f'Process industry: industry_id = {i} industry = {industry_name}')
    #     prompt = load_prompt('01-init-v2.txt', {
    #         'industry_name': industry_name,
    #     })
    #     expenses = ''
    #     for config in llm_configs:
    #         if config['name'] != 'openai':
    #             continue
    #         expenses = expenses + '\n' + ask_llm(config, prompt) + '\n'
    #     logging.info(f'Step 1: gather expenses, industry_id={i}\n{expenses}')
    #     save_file(f'{i}_expense_list.md', expenses)

    # # step 2 - merge lists
    # for i in target_industries:
    #     industry_name = industries[i]
    #     expenses = load_file(f'{i}_expense_list.md')
    #     prompt = load_prompt('02-merge-lists-v2.txt', {
    #         'industry_name': industry_name,
    #         'list': expenses
    #     })
    #     # объединяем статьи (используем одну LLM, любая должна справиться)
    #     merged_expenses = ask_llm(llm_configs[0], prompt)
    #     logging.info(f'Step 2: merged list, industry_id={i}\n{merged_expenses}')
    #     save_file(f'{i}_expense_merged.md', merged_expenses)

    # step 3 - add sum
    for i in target_industries:
        industry_name = industries[i]
        # expenses = load_file(f'{i}_expense_merged.md')
        expenses = load_file(f'{i}_expense_list.md')
        for r in target_regions:
            region_name = regions[r]
            inv_dict = segm_by_reg_ind.get((r, i))
            if inv_dict == None:
                logging.error(f'Not found: industry_id={i} region_id={r}')
                continue
            budget_s = inv_dict.get('S')
            budget_m = inv_dict.get('M')
            budget_l = inv_dict.get('L')
            prompt = load_prompt('03-add-sum-v2.txt', {
                'industry_name': industry_name,
                'region_name': region_name,
                'list': expenses,
                'budget_s': str(budget_s),
                'budget_m': str(budget_m),
                'budget_l': str(budget_l),
            })
            # добавляем суммы
            expenses_with_sum = ''
            for config in llm_configs:
                # получаем ответ от LLM на наш промпт
                expenses_with_sum = expenses_with_sum + '\n' + ask_llm(config, prompt) + '\n'
            logging.info(f'Step 3: list with sum, industry_id={i}, region_id={r}\n{expenses_with_sum}')
            save_file(f'{i}_{r}_expense_sum.md', expenses_with_sum)

    # # step 4 - avg sum
    # for i in target_industries:
    #     for r in target_regions:
    #         expenses = load_file(f'{i}_{r}_expense_sum.md')
    #         prompt = load_prompt('04-avg-v2.txt', {
    #             'list': expenses
    #         })
    #         avg_expenses = ask_llm(llm_configs[0], prompt)
    #         logging.info(f'Step 4: calc stats, industry_id={i}, region_id={r}\n{expenses}')
    #         save_file(f'{i}_{r}_expense_avg.md', avg_expenses)
    #
    # # step 5 - save result
    # step5(target_industries, target_regions)


# save result
def step5(target_industries, target_regions):
    logging.info("Step 5: save result")
    for i in target_industries:
        for r in target_regions:
            logging.info(f'processing ind={i} reg={r}')
            expenses = load_file(f'{i}_{r}_expense_avg.md')
            lines = expenses.split('\n')
            header = load_header_line(lines[0])
            # iterate data with avg by lines
            for s in lines[1:]:
                if s == '':
                    continue
                values = get_line_values(s)
                if len(values) == 0:
                    continue
                expenses = {
                    'industry_id': i,
                    'region_id': r,
                    'industry': industries[i],
                    'region': regions[r],
                    'size': 'S',
                    'expense': values[header['Статья затрат']],
                    'amount': values[header['S_avg']],
                    'min': values[header['S_min']],
                    'max': values[header['S_max']],
                }
                append_output(expenses)
                expenses['size'] = 'M'
                expenses['amount'] = values[header['M_avg']]
                expenses['min'] = values[header['M_min']]
                expenses['max'] = values[header['M_max']]
                append_output(expenses)
                expenses['size'] = 'L'
                expenses['amount'] = values[header['L_avg']]
                expenses['min'] = values[header['L_min']]
                expenses['max'] = values[header['L_max']]
                append_output(expenses)


def get_line_values(line):
    values = []
    for v in line.split('|'):
        if v == '':
            continue
        v = v.strip()
        if v.startswith('-'):
            break
        values.append(v)
    return values


def load_header_line(line):
    header_dict = dict([])
    values = get_line_values(line)
    for i in range(len(values)):
        header_dict[values[i]] = i
    return header_dict


def save_file(filename, data):
    with open(CONFIG['data']['output'] + '/' + filename, 'w') as f:
        f.write(data)


def load_file(filename):
    with open(CONFIG['data']['output'] + '/' + filename, 'r') as f:
        return f.read()


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


if __name__ == "__main__":
    main()
