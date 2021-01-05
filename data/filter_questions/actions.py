# -*- coding: utf-8 -*-
import logging
from typing import Any, Dict, List, Text, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import (
    EventType,
)

logger = logging.getLogger(__name__)

FILTER_MAPPING_PATH = 'data/filter_questions/entities/filter_mapping.csv'
BFZ_URL = 'https://www.beratungsnetz-migration.de'

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

    def run(
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

            dispatcher.utter_message(text=f'Ich habe Angebote gefunden für: {display_filters}')
            dispatcher.utter_message(text=f'Die Ergebnisse stehen hier zu verfügung {url}')

        return []
