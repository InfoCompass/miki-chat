# -*- coding: utf-8 -*-
import logging
from typing import Any, Dict, List, Text, Optional
import json
from collections import defaultdict

from aiohttp import ClientSession

from nltk.stem import SnowballStemmer

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import (
    EventType, SlotSet
)

logger = logging.getLogger(__name__)

FILTER_MAPPING_PATH = 'data/filter_questions/entities/filter_mapping.csv'
FILTER_SYNONYMS_PATH = 'data/filter_questions/entities/filter_synonyms.csv'
BFZ_URL = ''
BFZ_API_URL = 'https://api.beratungsnetz-migration.de'


class ActionFilterResults(Action):
    """Display the results of a Filter Question request"""

    def name(self) -> Text:
        return "action_filter_results"

    def __init__(self):
        import pandas as pd

        df = pd.read_csv(FILTER_MAPPING_PATH)
        df = df.set_index('filter')
        self.filter_mapping = df.to_dict()
        self.filters = self.filter_mapping['display'].keys()

        df = pd.read_csv(FILTER_SYNONYMS_PATH)
        df = df.set_index('synonym')
        self.synonym_to_filter = df.to_dict()['filter']

        self.stemmer = SnowballStemmer('german')


    def _format(self, filters):
        filters = [f'`{filter}`' for filter in filters]
        init = filters[:-1]
        last = filters[-1]
        if not init:
            return last
        else:
            return f'{", ".join(init)} und {last}'
        return filters


    # TODO:
    #  - Extract text into top of the file for ease of maintenance
    def _template_filters(self, filters):
        display_filters = [self.filter_mapping['display'][filter] for filter in filters]
        d_filters = defaultdict(list)

        for filter in filters:
            d_filters[self.filter_mapping['context'][filter]] += [self.filter_mapping['display'][filter]]

        if {'_topic', '_targetgroup', '_language', '_searchterms'} >= set(d_filters.keys()):

            if '_targetgroup' in d_filters:
                target_group = f' für {self._format(d_filters["_targetgroup"])}'
            else:
                target_group = ''

            if '_topic' in d_filters or '_searchterms' in d_filters:
                topic = f' zum Thema {self._format(d_filters["_topic"] + d_filters["_searchterms"])}'
            else:
                topic = ''

            if '_language' in d_filters:
                language = f' auf {self._format(d_filters["_language"])}'
            else:
                language = ''

            return f'Sie möchten wissen welche Angebote es{target_group} im BfZ{topic}{language} gibt'

        else:
            return f'Sie möchten wissen welche Angebote es für : {self._format(display_filters)} gibt'


    def _bfz_url(self, filters):
        key_filters = [(self.filter_mapping['filter_category'][filter], filter) for filter in filters]
        keys = set([k for k, _ in key_filters])

        # The special case where two filters share the same key, they have to be concatenated with dash
        # and passed together as a parameter
        url_filters = ['/' + k + '/' +
                       '-'.join([filter for k2, filter in key_filters if k==k2])
                       for k in keys]

        url_filters = ''.join(url_filters)
        return f'{BFZ_URL}/list{url_filters}'


    # TODO:
    #   - Handle exceptions in request
    async def _num_bfz_documents(self, filters):
        async with ClientSession() as session:

            search_filters = [f for f in filters if self.filter_mapping['is_search_term'][f]]
            filters = [f for f in filters if not self.filter_mapping['is_search_term'][f]]

            if search_filters:
                search_param = f'&search={search_filters[0]}'
            else:
                search_param = ''

            if filters:
                tag_param = ('tag' if len(filters)==1 else 'tags')
                tag_param = f'&{tag_param}={",".join(filters)}'
            else:
                tag_param = ''

            url = f'{BFZ_API_URL}/actions/exportItems?format=JSON&keys=id{tag_param}{search_param}'

            resp = await session.request(method="GET", url=url)
            resp.raise_for_status()
            res = await resp.text()
            num_documents = len(json.loads(res))
            logger.info(f'Issued backend request to {url} with {num_documents} results')
        return num_documents

    # TODO:
    #   - Extract text into top of the file for ease of maintenance
    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[EventType]:
        raw_filters = list(tracker.get_latest_entity_values("filter"))

        filters = []
        for f in raw_filters:
            if f in self.filters:
                filters.append(f)
            else:
                # This filter was picked up as an entity but not synonym resolved, let's try a custom resolution
                stemmed = self.stemmer.stem(f)
                if stemmed in self.synonym_to_filter:
                    logger.info(f'Resolving synonym {f} to {self.synonym_to_filter[stemmed]}')
                    filters.append(self.synonym_to_filter[stemmed])

        if not filters:
            dispatcher.utter_message(template='utter_keywords_not_understood', keywords=self._format(raw_filters))
            action_filter_error = 'keyword_not_understood'
        else:
            dispatcher.utter_message(text=self._template_filters(filters))

            num_documents = await self._num_bfz_documents(filters)
            if num_documents:
                dispatcher.utter_message(template='utter_results_found', results_url=self._bfz_url(filters))
                action_filter_error = None
            else:
                dispatcher.utter_message(template='utter_no_results_found')
                action_filter_error = 'no_results_found'

        return [SlotSet('action_filter_error', action_filter_error)]


class ResetActionFilterError(Action):
    """Absolute hacky way of resetting the slot but I can't think of a better way to do this in Rasa"""


    def name(self) -> Text:
        return 'reset_action_filter_error'


    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[EventType]:
        return [SlotSet('action_filter_error', None)]
