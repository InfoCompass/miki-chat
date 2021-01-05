import os
import re
import argparse
from collections import namedtuple, OrderedDict
import yaml
import pandas as pd

import gspread
from gspread.models import Cell
from oauth2client.service_account import ServiceAccountCredentials

def main():
    args = get_args()
    spreadsheet = open_spreadsheet(args)

    # Create directory structure
    os.makedirs(f'{args.output_dir}/data/faq', exist_ok=True)
    os.makedirs(f'{args.output_dir}/data/filter_questions/entities', exist_ok=True)

    # Dump FAQ NLU data
    question_rows = get_question_sheet(spreadsheet)
    with open(f'{args.output_dir}/data/faq/nlu.yml', 'w') as f:
        faq = questions_answers_nlu_data(args, question_rows)
        f.write(yaml.dump(faq, allow_unicode=True))

    filter_rows = get_filter_keyword_sheet(spreadsheet)
    filter_rows = filter_keywords(args, filter_rows)

    filters_df(filter_rows).to_csv(f'{args.output_dir}/data/filter_questions/entities/filter_mapping.csv', index=False)

    with open(f'{args.output_dir}/data/filter_questions/entities/nlu.yml', 'w') as f:
        nlu = filters_nlu_data(filter_rows)
        f.write(yaml.dump(nlu, allow_unicode=True))

    synonyms = [syn for row in filter_rows for syn in [row.keyword] + row.synonyms]
    filter_questions_logs, nlu = filter_questions_nlu_data(question_rows, synonyms)
    with open(f'{args.output_dir}/data/filter_questions/nlu.yml', 'w') as f:
        f.write(yaml.dump(nlu, allow_unicode=True))

    # save_logs(spreadsheet, filter_questions_logs)


def save_logs(spreadsheet, filter_questions_logs):
    worksheet = spreadsheet.worksheet("Logs")
    save_df(worksheet, filter_questions_logs, 1, 10)

def save_df(worksheet, df, init_col, init_row):
    total_cells = []
    for col_name, col in zip(df.columns.values, range(len(df.columns.values))):
        vals = df[col_name].values
        header = Cell(init_row, col + init_col, col_name)
        cells = [Cell(init_row+row+1, col + init_col, str(val)) for val, row in zip(vals, range(len(vals)))]
        total_cells.extend([header])
        total_cells.extend(cells)
    worksheet.update_cells(total_cells)


#################
# Spreadsheet processing logic
#################

Question = namedtuple('Question', 'intent question question_variants answer')


def filter_keywords(args, filter_rows):
    gs = group_by_column(filter_rows, 'context')

    filters_with_key = [row._replace(key=rows[0].key)
                        for _, rows in gs.items() if rows[0].key
                        for row in rows]
    filters_with_key_and_filter = [row for row in filters_with_key if row.filter]
    return filters_with_key_and_filter

def filters_df(filter_rows):
    return pd.DataFrame({
        'filter': [r.filter for r in filter_rows],
        'display': [r.keyword for r in filter_rows],
        'filter_category': [r.key for r in filter_rows]
    }).sort_values('filter')

def filters_nlu_data(filter_rows):
    return OrderedDict({
        'version': '2.0',
        'nlu':
            [OrderedDict(
                {
                    'synonym': r.filter,
                    'examples': format_examples([r.keyword] + r.synonyms)
                }
             )
             for r in filter_rows]
    })

def questions_answers_nlu_data(args, question_rows):
    gs = group_by_column(question_rows, 'intention')
    bfz_questions = group_by_column(gs['/bfz'], 'context')

    questions = [Question(f'bfz_{intent[1:]}',
                          rows[0].question,
                          [r.question_variant for r in rows if r.question_variant is not ''],
                          rows[0].answer)
                 for intent, rows in bfz_questions.items()
                 if rows[0].question]

    # Create faq yaml
    faq = OrderedDict({
        'version': '2.0',
        'nlu':
            [OrderedDict(
                {'intent': f'faq/{q.intent}',
                 'examples': format_examples([q.question] + [v for v in q.question_variants])})
                for q in questions],
        'responses':
            OrderedDict(
                {f'utter_faq/{q.intent}': [{'text': q.answer}]
                 for q in questions})
    })

    return faq

TaggedQuestion = namedtuple('TaggedQuestion', 'question entities auto_entities invalid_entities is_valid reason_invalid')

def process_question(synonyms, question):
    # Find all text marked by square braces
    tagged_entities = re.findall(r'\[[^\[]*\]', question)
    tagged_entities = [t[1:-1] for t in tagged_entities]
    tagged_entities = set(tagged_entities)

    invalid_entities = list(tagged_entities - synonyms)

    remaining_synonyms = list(synonyms - tagged_entities)

    new_entities = []
    tagged_entities = list(tagged_entities)

    # Order remaining synonyms by larger to smaller to avoid accidental matches
    remaining_synonyms = sorted([(len(s), s) for s in remaining_synonyms], reverse=True)
    remaining_synonyms = [s[1] for s in remaining_synonyms]

    for syn in remaining_synonyms:
        if not [syn in s for s in new_entities + tagged_entities]:
            # Make sure that analyzed new synonym is not a substring of an existing tag
            i = question.find(syn)
            if i>=0 and (i+len(syn) >= len(question) or question[i+len(syn)] in ' .,?'):
                new_entities.append(syn)
                question = question[:i] + '[' + syn + ']' + question[i+len(syn):]

    if invalid_entities:
        reason_invalid = 'Invalid entities found'
    elif not (new_entities + tagged_entities):
        reason_invalid = 'No valid entities found'
    else:
        reason_invalid = ''

    return TaggedQuestion(question, tagged_entities, new_entities, invalid_entities, not reason_invalid, reason_invalid)

def filter_questions_nlu_data(question_rows, synonyms):

    def rasa_tagging(s):
        '''Replaces, appends all entities tagged with a square bracket with a annotation (filter)'''
        return re.sub(r'\[([^\[]*)\]', '[\\1](filter)', s)

    synonyms = set(synonyms)
    gs = group_by_column(question_rows, 'intention')
    content_questions = gs['/content']

    qs = [process_question(synonyms, r.question_variant) for r in content_questions if r.question_variant]

    vqs = [q for q in qs if q.is_valid]

    logs = pd.DataFrame(qs).sort_values('is_valid', ascending=False)

    return logs, OrderedDict({
        'version': '2.0',
        'nlu':
            [OrderedDict(
                {
                    'intent': 'filter_question',
                    'examples': format_examples([rasa_tagging(q.question) for q in vqs])
                }
            )]
    })


def format_examples(qs):
    return '\n'.join([f'- {q}' for q in qs if q])


def group_by_column(rows, col):
    groups = {}
    current_val = None
    current = []
    for r in rows:
        if getattr(r, col)!='':
            if current_val:
                groups[current_val] = current
            current_val = getattr(r, col)
            current = [r]
        else:
            current.append(r)
    if current_val:
        groups[current_val] = current
    return groups

#################
# Utility Functions
#################

def get_args():
    parser = argparse.ArgumentParser(description="Import Question and Answer examples from BfZ spreadsheet")
    parser.add_argument('--client-secret', type=str, help='Path to json key file of service account', required=True)
    parser.add_argument('--spreadsheet-url', type=str, help='URL of Google Spreadsheet containing Questions and Answers', required=True)
    parser.add_argument('--output-dir', type=str, help='Directory name where output will be saved', required=True)
    return parser.parse_args()


def open_spreadsheet(args):
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(args.client_secret, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(args.spreadsheet_url)
    return spreadsheet


def get_question_sheet(spreadsheet):
    # Raw rows of the question spreadsheet
    Row = namedtuple('Row', 'intention context question question_variant answer')

    sheet = spreadsheet.worksheet("Fragenkatalog")
    list_of_hashes = sheet.get_all_records()

    rows = [Row(r['Context'], r['Intent'], r['Beschreibung / Beispiel'], r['Fragen (Varianten)'], r['Antwort_Part1'])
            for r in list_of_hashes]
    return rows


def get_filter_keyword_sheet(spreadsheet):

    def clean(s):
        return '(' not in s

    # Raw rows of the question spreadsheet
    Row = namedtuple('Row', 'context key filter keyword synonyms')

    sheet = spreadsheet.worksheet("Schlüsselwörter")
    list_of_hashes = sheet.get_all_records()

    rows = [Row(r['Context'], r['Key'], r['Filter'], r['Schlüsselwörter'],
                [r[f'Synonym {i}'] for i in range(1,6) if r[f'Synonym {i}'] and clean(r[f'Synonym {i}'])])
            for r in list_of_hashes]
    return rows

#################
# YAML rendering setup
#################

def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

def ordered_dict_presenter(dumper, data):
    return dumper.represent_dict(data.items())
yaml.add_representer(OrderedDict, ordered_dict_presenter)
yaml.add_representer(str, str_presenter)


# Run the main function
main()


