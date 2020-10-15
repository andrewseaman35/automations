from collections import defaultdict
from datetime import date
import json
import os
import re
import sys

FILENAME_REGEX = re.compile(r"^Chase(?P<card>\d{4})_Activity(?P<start_year>\d{4})(?P<start_month>\d{2})(?P<start_day>\d{2})_(?P<end_year>\d{4})(?P<end_month>\d{2})(?P<end_day>\d{2})_(\d{8}).CSV$")

DATE_FORMAT = '%Y %b %d'
CONFIG_FILE_NAME = './config.json'
IN_DIR = './inputs'
OUT_DIR = './output'

PAYMENT_CATEGORY = 'payments'
SKIP_KEYWORDS = {'skip'}


class Config(object):
    def __init__(self, filename):
        self.filename = filename
        self._config = None
        self.categories = None
        self.categorization = None
        self.unshared_categories = None
        self.reload()

    def reload(self):
        self._config = json.load(open(self.filename, 'r'))
        self.categories = sorted(self._config['categorization'].keys())
        self.categorization = self._config['categorization']
        self.unshared_categories = set(self._config['unshared_categories'])
        self.search_terms = self.get_search_term_dict()

    def serialize(self):
        return json.dumps(self._config, indent=4, sort_keys=True)

    def add_keyword_to_known_categorization(self, category, keyword):
        existing_keywords = set(self.categorization[category])
        if keyword in existing_keywords:
            return

        self.categorization[category].append(keyword)
        with open(self.filename, 'w') as f:
            f.write(self.serialize())
        self.reload()

    def get_search_term_dict(self):
        search_term_to_category = {}
        for category, terms in self.categorization.items():
            for term in terms:
                if term in search_term_to_category:
                    raise Exception('repeated term in categorization: {}'.format(term))
                search_term_to_category[term.lower()] = category.lower()
        return search_term_to_category


_config = Config(CONFIG_FILE_NAME)


class Transaction(object):
    def __init__(self, transaction_date, post_date, description, chase_category, type, amount):
        self.transaction_date = transaction_date
        self.post_date = post_date
        self.description = description.lower()
        self.chase_category = chase_category
        self.type = type
        self.amount = float(amount.strip()) * -1
        self.is_payment = self.amount < 0
        self.our_category = None

    def categorize(self, update_config):
        return self.ask_for_category(
            [c for c in _config.categories if c != PAYMENT_CATEGORY],
            update_config,
        )

    def ask_for_keyword(self):
        inp = input('Keyword for "{}": '.format(self.description))
        if inp.lower() in SKIP_KEYWORDS:
            return None
        if not inp:
            return self.description
        if inp not in self.description:
            raise Exception('{} not in {}'.format(inp, self.description))
        return inp

    def ask_for_category(self, categories, update_config):
        category_inputs = {}
        category_text = []
        for i, cat in enumerate(categories, start=1):
            category_inputs[str(i)] = cat
            category_text.append('({}) {}'.format(i, cat))

        print("Input category for '{}' (${}) ({})".format(
            self.description,
            self.amount,
            self.transaction_date,
        ))
        inp = input('{}\n'.format('\n'.join(category_text)))
        category = category_inputs[str(inp)]

        if update_config:
            keyword = self.ask_for_keyword()
            if keyword is not None:
                _config.add_keyword_to_known_categorization(category, keyword)
            else:
                print("  - skipped -")

        return category

    def confirm_category(self, category, term):
        inp = input('Confirm category for "{}": "{}", found by "{}": '.format(
            self.description,
            category,
            term,
        ))
        if 'n' in inp:
            return False
        return True

    def set_our_category(self, confirm=False, update_config=False):
        search_terms = _config.search_terms
        found_terms = set()
        if (self.is_payment):
            self.our_category = PAYMENT_CATEGORY
            return

        for term in search_terms:
            if term in self.description:
                found_terms.add(term)

        found_categories = {search_terms[t] for t in found_terms}
        if len(found_categories) == 1:
            found_term = next(iter(found_terms))
            found_category = next(iter(found_categories))
            if not confirm or self.confirm_category(found_category, found_term):
                self.our_category = search_terms[found_term]
            else:
                self.our_category = self.categorize(False)
        elif len(found_categories) > 1:
            self.our_category = self.ask_for_category(found_categories, update_config)
        else:
            self.our_category = self.categorize(update_config)


def parse_filename(filename):
    match = FILENAME_REGEX.match(filename)
    if not match:
        return None
    groups = match.groupdict()
    start_date = date(int(groups['start_year']), int(groups['start_month']), int(groups['start_day']))
    end_date = date(int(groups['end_year']), int(groups['end_month']), int(groups['end_day']))
    return {
        'card': groups['card'],
        'start_date': start_date,
        'formatted_start_date': start_date.strftime(DATE_FORMAT),
        'end_date': end_date,
        'formatted_end_date': end_date.strftime(DATE_FORMAT),
    }


def load_config():
    return json.load(open(CONFIG_FILE_NAME, 'r'))


def load_transactions(transaction_file_name):
    _transactions = []
    with open ('{}'.format(transaction_file_name), 'r') as f:
        f.readline()
        for line in f:
            transaction = Transaction(*line.split(','))
            _transactions.append(transaction)
    return sorted(_transactions, key=lambda t: t.transaction_date)


def do_work(filename):
    transactions = load_transactions(filename)
    total = len(transactions)
    for i, transaction in enumerate(transactions, start=1):
        print('\n{}/{}'.format(i, total))
        transaction.set_our_category(confirm=False, update_config=True)
    return transactions


def get_filenames(indir):
    chase_inputs = sorted(
        [f for f in os.listdir(indir) if os.path.isfile(os.path.join(indir, f)) and parse_filename(f)],
        key=lambda fn: parse_filename(fn)['start_date']
    )
    filename_to_parsed = {f: parse_filename(f) for f in chase_inputs}
    for i, ci in enumerate(chase_inputs, start=1):
        filename_to_parsed[ci]['index'] = i
        print('({index}): {card} | {start} - {end}'.format(
            index=filename_to_parsed[ci]['index'],
            card=filename_to_parsed[ci]['card'],
            start=filename_to_parsed[ci]['start_date'].strftime(DATE_FORMAT),
            end=filename_to_parsed[ci]['end_date'].strftime(DATE_FORMAT),
        ))
    indexes = input('\nSelect files (space separated): ')
    indexes = [int(i)-1 for i in indexes.split(' ')]
    return [chase_inputs[i] for i in indexes]


def validate_file_dates(parsed_filenames):
    start_dates = set([pf['start_date'] for pf in parsed_filenames])
    end_dates = set([pf['end_date'] for pf in parsed_filenames])
    assert len(set(start_dates)) == 1, 'multiple start_dates: {}'.format(start_dates)
    assert len(set(end_dates)) == 1, 'multiple end_dates: {}'.format(end_dates)


def run():
    all_transactions = []
    filenames = get_filenames(IN_DIR)
    parsed_filename_by_filename = {
        os.path.basename(f): parse_filename(os.path.basename(f)) for f in filenames
    }
    validate_file_dates(parsed_filename_by_filename.values())

    output_filename = None
    for filename in filenames:
        filename = os.path.join(IN_DIR, filename)
        parsed_filename = parsed_filename_by_filename[os.path.basename(filename)]
        if output_filename is None:
            output_filename = '{start}-{end}.csv'.format(
                start=parsed_filename['formatted_start_date'].replace(' ', '_'),
                end=parsed_filename['formatted_end_date'].replace(' ', '_'),
            )
        print(" == {} ==".format(parsed_filename['card']))
        all_transactions.extend(do_work(filename))

    total_total = 0
    transactions_by_category = {c: [] for c in _config.categories}
    total_by_category = {c: 0 for c in _config.categories}
    for transaction in sorted(all_transactions, key=lambda t: t.transaction_date):
        transactions_by_category[transaction.our_category].append(transaction)
        total_by_category[transaction.our_category] += transaction.amount
        total_total += 0 if transaction.is_payment else transaction.amount

    summary_parsed = parsed_filename_by_filename[next(iter(parsed_filename_by_filename.keys()))]
    summary_line_headers = ['Date']
    summary_line_values = ['{}-{}'.format(summary_parsed['start_date'].year, summary_parsed['start_date'].year)]
    for category in [c for c in _config.categories if c != PAYMENT_CATEGORY]:
        summary_line_headers.append(category)
        summary_line_values.append(round(total_by_category[category], 2))
    summary_line_headers.append('Total')
    summary_line_values.append(total_total)
    summary_line_headers.append('Total Shared')
    summary_line_values.append(round(total_total - sum(total_by_category[cat] for cat in _config.unshared_categories), 2))

    with open('{}/{}'.format(OUT_DIR, output_filename), 'w') as f:
        f.write('{},{},{},{}\n'.format(
            'transaction_date',
            'description',
            'amount',
            'category',
        ))
        for category in _config.categories:
            for transaction in transactions_by_category[category]:
                f.write('{},{},{},{}\n'.format(
                    transaction.transaction_date,
                    transaction.description,
                    transaction.amount,
                    category,
                ))
            f.write('\n')

        f.write('\n')
        for category in _config.categories:
            f.write('{},{}\n'.format(category, round(total_by_category[category], 2)))

        f.write('\n')
        f.write(','.join([str(h) for h in summary_line_headers]))
        f.write('\n')
        f.write(','.join([str(v) for v in summary_line_values]))
        f.write('\n')

if __name__ == '__main__':
    run()
