import logging
from pathlib import Path

from myglobal import CONFIG, load_file_lines, save_file, save_file_lines


def main():
    logging.info(f'Step 2 (postprocess): align expense''s names')
    llm_name = 'gigachat'

    # files_from_step1 = [f.name for f in Path(CONFIG['data']['output']).iterdir()
    #                     if f.is_file() and 'expense_list' in f.name]
    # for f1 in files_from_step1:
    #     expense_list = load_expense_list(f1)
    #     industry_id = f1.split('_')[0]
    #     for f2 in [f.name for f in Path(CONFIG['data']['output']).iterdir()
    #                if f.is_file() and industry_id + '_' in f.name and llm_name + '_expense_sum' in f.name]:
    #         print(f2)

    for f2 in [f.name for f in Path(CONFIG['data']['output']).iterdir()
               if f.is_file() and llm_name + '_expense_sum' in f.name]:
        align(f2)


def align(filename):
    # print('Processing {}'.format(filename))
    lines = load_file_lines(filename)
    expenses = []
    merged = False
    for line in lines:
        parts = [s.strip() for s in line.split('|')]
        if need_merge(parts):
            last_idx = len(expenses) - 1
            expenses[last_idx]['item'] += ' ' + parts[1]
            expenses[last_idx]['s'] = expenses[last_idx]['s'] if expenses[last_idx]['s'] != '' else parts[2]
            expenses[last_idx]['m'] = expenses[last_idx]['m'] if expenses[last_idx]['m'] != '' else parts[3]
            expenses[last_idx]['l'] = expenses[last_idx]['l'] if expenses[last_idx]['l'] != '' else parts[4]
            merged = True
            continue
        expenses.append({
            'item': parts[1],
            's': parts[2],
            'm': parts[3],
            'l': parts[4],
        })
    if not merged:
        return

    print('Need Alignment {}'.format(filename))
    # lines = []
    # for e in expenses:
    #     lines.append(f'| {e['item']} | {e['s']} | {e['m']} | {e['l']} |\n')
    # save_file_lines(filename, lines)


def need_merge(parts):
    # not need to merge in case if expense title starts with uppercase
    if parts[1][0].isupper():
        return False
    # split line '-'
    if '-' in parts[1] and '-' in parts[2] and '-' in parts[3] and '-' in parts[4]:
        return False
    # otherwise we need to merge
    return True


if __name__ == "__main__":
    main()
