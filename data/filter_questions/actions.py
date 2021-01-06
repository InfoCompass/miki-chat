# -*- coding: utf-8 -*-
import logging
from typing import Any, Dict, List, Text, Optional
import json

from aiohttp import ClientSession

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import (
    EventType,
)

logger = logging.getLogger(__name__)

FILTER_MAPPING_PATH = 'data/filter_questions/entities/filter_mapping.csv'
BFZ_URL = 'https://www.beratungsnetz-migration.de'
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
    #   - Handle exceptions in request
    #   - Basic copy
    #   - More fancy copy
    async def _num_bfz_documents(self, filters):
        async with ClientSession() as session:
            url = f'{BFZ_API_URL}/actions/exportItems?format=JSON&keys=id&tags={",".join(filters)}'
            resp = await session.request(method="GET", url=url)
            resp.raise_for_status()
            res = await resp.text()
            num_documents = len(json.loads(res))
        return num_documents

    async def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any],
    ) -> List[EventType]:
        filters = list(tracker.get_latest_entity_values("filter"))
        filters = list(set(filters) & set(self.filters))

        if not filters:
            dispatcher.utter_message(text='Leider ich habe deine Anfrage nicht verstanden')
        else:
            display_filters = [self.filter_mapping['display'][filter] for filter in filters]
            display_filters = self._format(display_filters)

            key_filters = [(self.filter_mapping['filter_category'][filter], filter) for filter in filters]
            keys = set([k for k, _ in key_filters])

            # The special case where two filters share the same key, they have to be concatenated with dash
            # and passed together as a parameter
            url_filters = ['/' + k + '/' +
                           '-'.join([filter for k2, filter in key_filters if k==k2])
                           for k in keys]

            url_filters = ''.join(url_filters)
            url = f'{BFZ_URL}/list{url_filters}'

            dispatcher.utter_message(text=f'Du hast gefragt nach Angebote für: {display_filters}')

            num_documents = await self._num_bfz_documents(filters)

            if num_documents:
                dispatcher.utter_message(text=f'Es gibt {num_documents} ergebnisse zu Verfügung')
                dispatcher.utter_message(text=f'Du kannst die hier erreichen {url}')
            else:
                dispatcher.utter_message(text=f'Es wurde leider keine Dokumenten gefunden')

        return []
