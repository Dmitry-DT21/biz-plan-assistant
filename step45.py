from pathlib import Path

from myglobal import industries, regions


def main():
    BIG = 1_000_000_000
    # Get all items in the current directory and filter for files
    files = [f for f in Path('output').iterdir() if f.is_file() and 'sum' in f.name]

    problem_ind = set()
    for file in files:
        parts = file.name.split('_')
        industry_id = int(parts[0])
        region_id = int(parts[1])
        industry = industries[industry_id]
        region = regions[region_id]
        # print(f'{file.name} ind={industry_id} reg={region_id}')
        lines = load_file('output/' + file.name)
        expenses = dict([])
        for line in lines:
            cols = line.split('|')
            try:
                title = cols[1].strip()
                s = int(cols[2])
                m = int(cols[3])
                l = int(cols[4])
                rec = expenses.setdefault(title, {
                    'S': 0, 'M': 0, 'L': 0, 'n': 0,
                    'S_min': BIG, 'S_max': 0,
                    'M_min': BIG, 'M_max': 0,
                    'L_min': BIG, 'L_max': 0,
                })
                rec['S'] += s
                rec['M'] += m
                rec['L'] += l
                rec['n'] += 1
                rec['S_min'] = min(rec['S_min'], s)
                rec['S_max'] = max(rec['S_max'], s)
                rec['M_min'] = min(rec['M_min'], m)
                rec['M_max'] = max(rec['M_max'], m)
                rec['L_min'] = min(rec['L_min'], l)
                rec['L_max'] = max(rec['L_max'], l)
            except:
                continue
        for e, x in expenses.items():
            if x['n'] != 3:
                print(e, x)
                problem_ind.add(industry_id)
            for size in ['S', 'M', 'L']:
                print(f'{industry_id};{region_id};{industry};{region};{size};{e};{x[size]/x['n']:.0f};{x[size+'_min']};{x[size + '_max']}')

    # print(f'ALARMA {problem_ind}')


def load_file(filename):
    with open(filename) as f:
        return f.readlines()


if __name__ == "__main__":
    main()
