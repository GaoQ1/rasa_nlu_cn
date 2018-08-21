# Rasa NLU for Chinese, and is suppored by Spacy, a fork from RasaHQ/rasa_nlu

## Files you should have
 - data/wiki.zh.vec
You can download [*pretrained-vectors*](https://github.com/facebookresearch/fastText/blob/master/pretrained-vectors.md),
or you can train word vector by yourself.

# Usage

## 1.Clone this project, and run
```
python setup.py install
```

## 2.Modify configuration
Use Spacy + jieba
```
language: "zh"

pipeline:
- name: "nlp_spacy"
  model: "data/zh_models"
- name: "tokenizer_jieba"
- name: "intent_entity_featurizer_regex"
- name: "intent_featurizer_spacy"
- name: "ner_crf"
- name: "ner_synonyms"
- name: "intent_classifier_sklearn"
```

## 3.(Optional) Use Jieba User Defined Dictionary or Switch Jieba Default Dictionoary:
```
language: "zh"

pipeline:
- name: "nlp_spacy"
  model: "data/zh_models"
- name: "tokenizer_jieba"
  default_dict: "./default_dict.big"
  user_dicts: "./jieba_userdict"
- name: "intent_entity_featurizer_regex"
- name: "intent_featurizer_spacy"
- name: "ner_crf"
- name: "ner_synonyms"
- name: "intent_classifier_sklearn"
```

## 4.Load vector and generate model supported by Spacy
```
python -m rasa_nlu.load_vector data/wiki.zh.vec zh zh_models
```

## 5.Train model by running
```
python -m rasa_nlu.train -c sample_configs/config_spacy_jieba.yml --data data/examples/rasa/demo-rasa_zh.json --path models
```

## 6.Run the rasa_nlu server
```
python -m rasa_nlu.server -c sample_configs/config_spacy_jieba.yml --path models
```

## 7.Open a new terminal and now you can curl results from the server, for example:
```
$ curl -XPOST localhost:5000/parse -d '{"q":"我发烧了该吃什么药？", "model": "model_20180821-115735"}' | python -mjson.tool
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   652    0   552  100   100    157     28  0:00:03  0:00:03 --:--:--   157
{
    "entities": [
        {
            "end": 3,
            "entity": "disease",
            "extractor": "ner_mitie",
            "start": 1,
            "value": "发烧"
        }
    ],
    "intent": {
        "confidence": 0.5397186422631861,
        "name": "medical"
    },
    "intent_ranking": [
        {
            "confidence": 0.5397186422631861,
            "name": "medical"
        },
        {
            "confidence": 0.16206323981749196,
            "name": "restaurant_search"
        },
        {
            "confidence": 0.1212448457737397,
            "name": "affirm"
        },
        {
            "confidence": 0.10333600028547868,
            "name": "goodbye"
        },
        {
            "confidence": 0.07363727186010374,
            "name": "greet"
        }
    ],
    "text": "我发烧了该吃什么药？"
}
```