from pathlib import Path

from myglobal import industries, regions, CONFIG, load_file_lines

BIG = 1_000_000_000
ITEM = 'item'
N = 'n'
SIZE_S = 'S'
SIZE_M = 'M'
SIZE_L = 'L'
SUM = 'sum'
MIN = 'min'
MAX = 'max'
SIZES = [SIZE_S, SIZE_M, SIZE_L]


def main():
    # Get all items in the current directory and filter for files
    files = [f.name for f in Path(CONFIG['data']['output']).iterdir() if f.is_file() and 'sum' in f.name]

    # collecting dictionary ind_reg: key = (industry_id, region_id), value = dict {llm, file}
    ind_reg = {}
    for file in files:
        parts = file.split('_')
        industry_id = int(parts[0])
        region_id = int(parts[1])
        llm = parts[2]
        ind_reg.setdefault((industry_id, region_id), [])
        ind_reg[(industry_id, region_id)].append({
            'llm': llm,
            'filename': file,
        })

    # check completeness for 3 LLMs
    # ok = True
    # for (k, v) in ind_reg.items():
    #     if len(v) != 3:
    #         print(f'key = {k}, value = {v}')
    #         ok = False
    #         break
    # if not ok:
    #     print('Found some problems with data completeness')
    #     exit(1)

    # problems = {}
    for (ind_reg, file_info) in ind_reg.items():
        industry_id = ind_reg[0]
        region_id = ind_reg[1]
        industry = industries[industry_id]
        region = regions[region_id]

        expenses_united = []
        for x in file_info:
            # if x['llm'] in 'gigachat':
            #     continue
            prepared = prepare_data(x['filename'])
            expenses_united += prepared

        expenses_avg = {}
        for e in expenses_united:
            stat = expenses_avg.setdefault(e[ITEM], zero_stat_with_size())
            stat[N] += 1
            for size in SIZES:
                x = stat[size]
                v = e[size]
                x[SUM] += v
                x[MIN] = min(x[MIN], v)
                x[MAX] = max(x[MAX], v)

        # print(expenses_avg)

        for (e, stat) in expenses_avg.items():
            # for size in ['S', 'M', 'L']:
            for size in ['S']:
                x = stat[size]
                n = stat[N]
                if n != 3:
                    print('Problem ind_reg={}, {}, n={}'.format(ind_reg, e, n))
                # print(f'{industry_id};{region_id};{industry};{region};{size};{e};{x[SUM] / n:.0f};{x[MIN]};{x[MAX]}')

    # print(problems)


def zero_stat():
    return {
        SUM: 0,
        MIN: BIG,
        MAX: 0,
    }


def zero_stat_with_size():
    return {
        N: 0,
        SIZE_S: zero_stat(),
        SIZE_M: zero_stat(),
        SIZE_L: zero_stat(),
    }


def prepare_data(filename):
    lines = load_file_lines(filename)
    expenses = []
    for line in lines:
        cols = line.split('|')
        try:
            title = cols[1].strip()
            s = int(cols[2])
            m = int(cols[3])
            l = int(cols[4])
            expenses.append({
                ITEM: title,
                SIZE_S: s, SIZE_M: m, SIZE_L: l,
            })
        except:
            continue
    return expenses


if __name__ == "__main__":
    main()
