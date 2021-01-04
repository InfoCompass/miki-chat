import os
import argparse
from collections import namedtuple, OrderedDict
import yaml

import gspread
from oauth2client.service_account import ServiceAccountCredentials

parser = argparse.ArgumentParser(description="Import Question and Answer examples from BfZ spreadsheet")
parser.add_argument('--client-secret', type=str, help='Path to json key file of service account', required=True)
parser.add_argument('--spreadsheet-key', type=str, help='Key of Google Spreadsheet containing Questions and Answers', required=True)
parser.add_argument('--output-dir', type=str, help='Directory name where output will be saved', required=True)

args = parser.parse_args()

def open_spreadsheet(args):
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(args.client_secret, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(args.spreadsheet_key)
    return spreadsheet

spreadsheet = open_spreadsheet(args)

# Raw rows of the spreadsheet
Row = namedtuple('Row', 'intention context question question_variant answer')

def get_question_sheet(spreadsheet):
    sheet = spreadsheet.worksheet("Fragenkatalog")
    list_of_hashes = sheet.get_all_records()

    rows = [Row(r['Intention'], r['Kontext'], r['Beschreibung / Beispiel'], r['Fragen (Varianten)'], r['Antwort_Part1'])
            for r in list_of_hashes]
    return rows

rows = get_question_sheet(spreadsheet)

Question = namedtuple('Question', 'intent question question_variants answer')

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

gs = group_by_column(rows, 'intention')

bfz_questions = group_by_column(gs['/bfz'], 'context')

questions = [Question(f'bfz_{intent[1:]}',
                      rows[0].question,
                      [r.question_variant for r in rows if r.question_variant is not ''],
                      rows[0].answer)
             for intent, rows in bfz_questions.items()
             if rows[0].question]

def format_questions(qs):
    return ''.join([f'- {q}\n' for q in qs])

# YAML rendering setup

def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

def ordered_dict_presenter(dumper, data):
    return dumper.represent_dict(data.items())
yaml.add_representer(OrderedDict, ordered_dict_presenter)
yaml.add_representer(str, str_presenter)


# Create directory structure
os.makedirs(f'{args.output_dir}/data/faq', exist_ok=True)

# Dump faq NLU data

# Create faq yaml
faq = OrderedDict({
    'version': '2.0',
    'nlu':
        [OrderedDict(
            {'intent': f'faq/{q.intent}',
             'examples': format_questions([q.question] + [v for v in q.question_variants])})
            for q in questions],
    'responses':
        OrderedDict(
            {f'utter_faq/{q.intent}': [{'text': q.answer}]
             for q in questions})
})

with open(f'{args.output_dir}/data/faq/nlu.yml', 'w') as f:
    f.write(yaml.dump(faq, allow_unicode=True))
