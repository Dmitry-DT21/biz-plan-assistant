from myglobal import *


def main():
    logging.info("Generating expenses v2")
    target_industries = list(industries.keys())[:]

    # step 1 - get expenses list by every industry
    for i in target_industries:
        industry_name = industries[i]
        logging.info(f'Process industry: industry_id = {i} industry = {industry_name}')
        prompt = load_prompt('01-init-v2.txt', {
            'industry_name': industry_name,
        })
        expenses = ''
        for config in llm_configs:
            if config['name'] != 'openai':
                continue
            expenses = expenses + '\n' + ask_llm(config, prompt) + '\n'
        logging.info(f'Step 1: gather expenses, industry_id={i}\n{expenses}')
        save_file(f'{i}_expense_list.md', expenses)


if __name__ == "__main__":
    main()
