import argparse
from collections import namedtuple, OrderedDict
import yaml

import gspread
from oauth2client.service_account import ServiceAccountCredentials

parser = argparse.ArgumentParser(description="Import Question and Answer examples from BfZ spreadsheet")
parser.add_argument('--client-secret', type=str, help='Path to json key file of service account', required=True)
parser.add_argument('--spreadsheet-key', type=str, help='Key of Google Spreadsheet containing Questions and Answers', required=True)

args = parser.parse_args()
print(args)


scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(args.client_secret, scope)
client = gspread.authorize(creds)

sheet = client.open_by_key(args.spreadsheet_key).sheet1

# Extract and print all of the values
list_of_hashes = sheet.get_all_records()

# Raw rows of the spreadsheet
Row = namedtuple('Row', 'intention context question question_variant answer')

rows = [Row(r['Intention'], r['Kontext'], r['Beschreibung / Beispiel'], r['Fragen (Varianten)'], r['Antwort_Part1'])
        for r in list_of_hashes]

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


def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

def ordered_dict_presenter(dumper, data):
    return dumper.represent_dict(data.items())
yaml.add_representer(OrderedDict, ordered_dict_presenter)

yaml.add_representer(str, str_presenter)

print(yaml.dump(faq, allow_unicode=True))