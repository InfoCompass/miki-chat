import logging
from typing import Any, List, Type, Text, Dict, Union, Tuple, Optional

from rasa.core.constants import (
    DEFAULT_NLU_FALLBACK_THRESHOLD,
    DEFAULT_NLU_FALLBACK_AMBIGUITY_THRESHOLD,
)
from rasa.nlu.classifiers.classifier import IntentClassifier
from rasa.nlu.components import Component
from rasa.shared.nlu.training_data.message import Message
from rasa.shared.nlu.constants import (
    INTENT,
    INTENT_NAME_KEY,
    INTENT_RANKING_KEY,
    PREDICTED_CONFIDENCE_KEY,
)

THRESHOLD_KEY = "threshold"
INTENT_NAME = "intent_name"
MAX_NUM_TOKS = "maximum_num_tokens"
AMBIGUITY_THRESHOLD_KEY = "ambiguity_threshold"

logger = logging.getLogger(__name__)


# Based on FallbackClassifier from Rasa
class SingleTokenFallbackClassifier(IntentClassifier):

    # please make sure to update the docs when changing a default parameter
    defaults = {
        THRESHOLD_KEY: DEFAULT_NLU_FALLBACK_THRESHOLD,
        MAX_NUM_TOKS: 1,
        INTENT_NAME: 'single_token_intent',
    }

    @classmethod
    def required_components(cls) -> List[Type[Component]]:
        return [IntentClassifier]

    def process(self, message: Message, **kwargs: Any) -> None:
        if not self._should_fallback(message):
            return

        # we assume that the confidence of fallback is 1 - confidence of top intent
        confidence = 1 - message.data[INTENT][PREDICTED_CONFIDENCE_KEY]
        message.data[INTENT] = _fallback_intent(self.component_config[INTENT_NAME], confidence)
        message.data.setdefault(INTENT_RANKING_KEY, [])
        message.data[INTENT_RANKING_KEY].insert(0, _fallback_intent(self.component_config[INTENT_NAME], confidence))

    def _should_fallback(self, message: Message) -> bool:
        intent_name = message.data[INTENT].get(INTENT_NAME_KEY)
        below_threshold, nlu_confidence = self._nlu_confidence_below_threshold(message)
        toks = [tok for tok in message.data['text_tokens'] if tok.end - tok.start > 1]

        if below_threshold and len(toks) <= self.component_config[MAX_NUM_TOKS]:
            logger.debug(
                f"NLU confidence {nlu_confidence} for intent '{intent_name}' is lower "
                f"than NLU threshold {self.component_config[THRESHOLD_KEY]:.2f}."
            )
            return True

        return False

    def _nlu_confidence_below_threshold(self, message: Message) -> Tuple[bool, float]:
        nlu_confidence = message.data[INTENT].get(PREDICTED_CONFIDENCE_KEY)
        return nlu_confidence < self.component_config[THRESHOLD_KEY], nlu_confidence


def _fallback_intent(intent_name: str, confidence: float) -> Dict[Text, Union[Text, float]]:
    return {
        INTENT_NAME_KEY: intent_name,
        PREDICTED_CONFIDENCE_KEY: confidence,
    }


