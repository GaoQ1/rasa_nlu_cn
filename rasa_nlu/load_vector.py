from __future__ import unicode_literals
import plac
import numpy

import spacy
from spacy.language import Language

@plac.annotations(
    vectors_loc=("Path to .vec file", "positional", None, str),
    lang=("Optional language ID. If not set, blank Language() will be used.",
          "positional", None, str),
    model_name=("Model's name is required.",
          "positional", None, str))
def main(vectors_loc, lang=None, model_name='zh_model'):
    if lang is None:
        nlp = Language()
    else:
        # create an empty language class
        nlp = spacy.blank(lang)
    with open(vectors_loc, 'rb') as file_:
        header = file_.readline()
        nr_row, nr_dim = header.split()
        print(nr_row, nr_dim)

        nlp.vocab.reset_vectors(width=int(nr_dim))
        for line in file_:
            line = line.rstrip().decode('utf8')
            pieces = line.rsplit(' ', int(nr_dim))
            word = pieces[0]
            vector = numpy.asarray([float(v) for v in pieces[1:]], dtype='f')
            # add the vectors to the vocab
            nlp.vocab.set_vector(word, vector)
    nlp.to_disk("data/" + model_name)
    print('finishing!!!')

if __name__ == '__main__':
    plac.call(main)
