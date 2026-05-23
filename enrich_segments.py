from myglobal import *


def main():
    segment_investment = {}
    for segment in filtered_segments:
        segment_investment[(segment['industry_id'], segment['region_id'], segment['size'])] = int(segment['investment'])
    fieldnames = [ 'industry_id', 'region_id', 'industry', 'region', 'sizeofbusiness', 'initialinvestment' ]

    enriched_segments_file = 'data/segments-ex.csv'
    with open(enriched_segments_file, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=',')
        writer.writeheader()
        for segment in filtered_segments:
            row = {
                'industry_id': segment['industry_id'],
                'region_id': segment['region_id'],
                'industry': industries[segment['industry_id']],
                'region': regions[segment['region_id']],
                'sizeofbusiness': segment['size'],
                'initialinvestment': segment['investment'],
            }
            writer.writerow(row)

if __name__ == "__main__":
    main()
