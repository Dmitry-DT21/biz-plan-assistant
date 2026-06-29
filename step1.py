from myglobal import *


def main():
    logging.info("Generating expenses v3")
    target_industries = list(industries.keys())[:]

    target_config = None
    for config in llm_configs:
        if config['name'] == 'openai':
            target_config = config
            break

    # step 1 - get expenses list by every industry
    for i in target_industries:
        filename = f'{i}_list.md'
        if output_file_exists(filename):
            logging.info(f'Skipping industry_id={i}')
            continue
        industry_name = industries[i]
        logging.info(f'Process industry: industry_id = {i} industry = {industry_name}')
        prompt = load_prompt('01-init-v3.txt', {
            'industry_name': industry_name,
        })
        expenses = ask_llm(target_config, prompt) + '\n'
        logging.info(f'Step 1: gather expenses, industry_id={i}\n{expenses}')
        save_file(filename, expenses)


if __name__ == "__main__":
    main()
