from myglobal import *


def main():
    logging.info("Generating expenses v2")
    target_regions = [77, 78]
    target_industries = [1, 403]

    segm_by_reg_ind = get_investment(segments, target_regions, target_industries)
    logging.info(f'investments by (region, industry) = {segm_by_reg_ind}')

    # # step 1 - get expenses list by every industry
    # for i in target_industries:
    #     industry_name = industries[i]
    #     logging.info(f'Process industry: industry_id = {i} industry = {industry_name}')
    #     prompt = load_prompt('01-init-v2.txt', {
    #         'industry_name': industry_name,
    #     })
    #     expenses = ''
    #     for config in llm_configs:
    #         expenses = expenses + '\n' + ask_llm(config, prompt) + '\n'
    #     logging.info(f'Step 1:\n{expenses}')
    #     save_file(f'{i}_expense_list.md', expenses)
    #
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
    #     logging.info(f'Step 2: merged list\n{merged_expenses}')
    #     save_file(f'{i}_expense_merged.md', merged_expenses)

    # step 3 - add sum
    for i in target_industries:
        industry_name = industries[i]
        expenses = load_file(f'{i}_expense_merged.md')
        for r in target_regions:
            region_name = regions[r]
            inv_dict = segm_by_reg_ind.get((r, i))
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
            logging.info(prompt)


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
