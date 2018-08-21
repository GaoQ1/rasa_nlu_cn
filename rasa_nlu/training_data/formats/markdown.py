from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re
import logging

from rasa_nlu.training_data import Message, TrainingData
from rasa_nlu.training_data.util import check_duplicate_synonym
from rasa_nlu.utils import build_entity

from rasa_nlu.training_data.formats.readerwriter import TrainingDataReader, TrainingDataWriter

INTENT = "intent"
SYNONYM = "synonym"
REGEX = "regex"
available_sections = [INTENT, SYNONYM, REGEX]
ent_regex = re.compile(r'\[(?P<entity_text>[^\]]+)'
                       r'\]\((?P<entity>\w*?)'
                       r'(?:\:(?P<value>[^)]+))?\)')  # [entity_text](entity_type(:entity_synonym)?)

item_regex = re.compile(r'\s*[-\*+]\s*(.+)')
comment_regex = re.compile(r'<!--[\s\S]*?--!*>', re.MULTILINE)

logger = logging.getLogger(__name__)


class MarkdownReader(TrainingDataReader):
    """Reads markdown training data and creates a TrainingData object."""

    def __init__(self):
        self.current_title = None
        self.current_section = None
        self.training_examples = []
        self.entity_synonyms = {}
        self.regex_features = []
        self.section_regexes = self._create_section_regexes(available_sections)

    def reads(self, s, **kwargs):
        """Read markdown string and create TrainingData object"""
        self.__init__()
        s = self._strip_comments(s)
        for line in s.splitlines():
            line = line.strip()
            header = self._find_section_header(line)
            if header:
                self._set_current_section(header[0], header[1])
            else:
                self._parse_item(line)

        return TrainingData(self.training_examples, self.entity_synonyms, self.regex_features)

    @staticmethod
    def _strip_comments(text):
        """ Removes comments defined by `comment_regex` from `text`. """
        return re.sub(comment_regex, '', text)

    @staticmethod
    def _create_section_regexes(section_names):
        def make_regex(section_name):
            return re.compile(r'##\s*{}:(.+)'.format(section_name))

        return {sn: make_regex(sn) for sn in section_names}

    def _find_section_header(self, line):
        """Checks if the current line contains a section header and returns the section and the title."""
        for name, regex in self.section_regexes.items():
            match = re.search(regex, line)
            if match is not None:
                return name, match.group(1)
        return None

    def _parse_item(self, line):
        """Parses an md list item line based on the current section type."""
        match = re.match(item_regex, line)
        if match:
            item = match.group(1)
            if self.current_section == INTENT:
                parsed = self._parse_training_example(item)
                self.training_examples.append(parsed)
            elif self.current_section == SYNONYM:
                self._add_synonym(item, self.current_title)
            else:
                self.regex_features.append({"name": self.current_title, "pattern": item})

    def _find_entities_in_training_example(self, example):
        """Extracts entities from a markdown intent example."""
        entities = []
        offset = 0
        for match in re.finditer(ent_regex, example):
            entity_text = match.groupdict()['entity_text']
            entity_type = match.groupdict()['entity']
            entity_value = match.groupdict()['value'] if match.groupdict()['value'] else entity_text

            start_index = match.start() - offset
            end_index = start_index + len(entity_text)
            offset += len(match.group(0)) - len(entity_text)

            entity = build_entity(start_index, end_index, entity_value, entity_type)
            entities.append(entity)

        return entities

    def _add_synonym(self, text, value):
        check_duplicate_synonym(self.entity_synonyms, text, value, "reading markdown")
        self.entity_synonyms[text] = value

    def _add_synonyms(self, plain_text, entities):
        """Adds synonyms found in intent examples"""
        for e in entities:
            e_text = plain_text[e['start']:e['end']]
            if e_text != e['value']:
                self._add_synonym(e_text, e['value'])

    def _parse_training_example(self, example):
        """Extract entities and synonyms, and convert to plain text."""
        entities = self._find_entities_in_training_example(example)
        plain_text = re.sub(ent_regex, lambda m: m.groupdict()['entity_text'], example)
        self._add_synonyms(plain_text, entities)
        message = Message(plain_text, {'intent': self.current_title})
        if len(entities) > 0:
            message.set('entities', entities)
        return message

    def _set_current_section(self, section, title):
        """Update parsing mode."""
        if section not in available_sections:
            raise ValueError("Found markdown section {} which is not "
                             "in the allowed sections {},".format(section, ",".join(available_sections)))

        self.current_section = section
        self.current_title = title


class MarkdownWriter(TrainingDataWriter):

    def dumps(self, training_data):
        """Transforms a TrainingData object into a markdown string."""
        md = u''
        md += self._generate_training_examples_md(training_data)
        md += self._generate_synonyms_md(training_data)
        md += self._generate_regex_features_md(training_data)

        return md

    def _generate_training_examples_md(self, training_data):
        """generates markdown training examples."""
        training_examples = sorted([e.as_dict() for e in training_data.training_examples],
                                   key=lambda k: k['intent'])
        md = u''
        for i, example in enumerate(training_examples):
            if i == 0 or training_examples[i - 1]['intent'] != example['intent']:
                md += self._generate_section_header_md(INTENT, example['intent'], i != 0)

            md += self._generate_item_md(self._generate_message_md(example))

        return md

    def _generate_synonyms_md(self, training_data):
        """generates markdown for entity synomyms."""
        entity_synonyms = sorted(training_data.entity_synonyms.items(),
                                 key=lambda x: x[1])
        md = u''
        for i, synonym in enumerate(entity_synonyms):
            if i == 0 or entity_synonyms[i - 1][1] != synonym[1]:
                md += self._generate_section_header_md(SYNONYM, synonym[1])

            md += self._generate_item_md(synonym[0])

        return md

    def _generate_regex_features_md(self, training_data):
        """generates markdown for regex features."""
        md = u''
        # regex features are already sorted
        regex_features = training_data.regex_features
        for i, regex_feature in enumerate(regex_features):
            if i == 0 or regex_features[i - 1]["name"] != regex_feature["name"]:
                md += self._generate_section_header_md(REGEX, regex_feature["name"])

            md += self._generate_item_md(regex_feature["pattern"])

        return md

    def _generate_section_header_md(self, section_type, title, prepend_newline=True):
        """generates markdown section header."""
        prefix = "\n" if prepend_newline else ""
        return prefix + "## {}:{}\n".format(section_type, title)

    def _generate_item_md(self, text):
        """generates markdown for a list item."""
        return "- {}\n".format(text)

    def _generate_message_md(self, message):
        """generates markdown for a message object."""
        md = ''
        text = message.get('text')
        entities = sorted(message.get('entities', []),
                          key=lambda k: k['start'])

        pos = 0
        for entity in entities:
            md += text[pos:entity['start']]
            md += self._generate_entity_md(text, entity)
            pos = entity['end']

        md += text[pos:]

        return md

    def _generate_entity_md(self, text, entity):
        """generates markdown for an entity object."""
        entity_text = text[entity['start']:entity['end']]
        entity_type = entity['entity']
        if entity_text != entity['value']:
            # add synonym suffix
            entity_type += ":{}".format(entity['value'])

        return '[{}]({})'.format(entity_text, entity_type)
