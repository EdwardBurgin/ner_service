import os
from pathlib import Path

import spacy
from flask import Flask, jsonify
from flask_restful import Resource, Api, reqparse
from jinja2.nodes import List
from joblib import load
import numpy as np
import sys
import os

# MODEL_DIR = os.environ["MODEL_DIR"]
# MODEL_FILE = os.environ["MODEL_FILE"]
# METADATA_FILE = os.environ["METADATA_FILE"]
# MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILE)
# METADATA_PATH = os.path.join(MODEL_DIR, METADATA_FILE)

# print("Loading model from: {}".format(MODEL_PATH))
# clf = load(MODEL_PATH)
from spacy import Language
from spacy.cli import project_assets, project_run
from spacy.tokens.doc import Doc
from spacy.training.iob_utils import biluo_tags_from_offsets

app = Flask(__name__)
api = Api(app)

import flask
flask.__version__


nlp = None
project_dir = "project-ner"
model_path = '/'.join([project_dir, 'training/model-best'])


class CustomSpacyNER(Resource):
    def __init__(self) -> None:
        self._required_features = ['entities', 'params']
        # self._required_features = ['text']
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(
            'text', type=list, required=True, location='json',
            help='No {} provided'.format('text'))
        for feature in self._required_features:
            self.reqparse.add_argument(
                feature, type=list, required=False, location='json',
                help='No {} provided'.format(feature))
        super(CustomSpacyNER, self).__init__()

    @staticmethod
    def load_model(spacy_model_name: str) -> "Language":
        """Try loading the model, catching the OSError if missing."""
        try:
            return spacy.load(spacy_model_name, disable=["parser"])
        except OSError:
            raise FileNotFoundError(
                "Model '{}' is not a linked spaCy model.  "
                "Please download and/or link a spaCy model, "
                "e.g. by running:\npython -m spacy download "
                "en_core_web_md\npython -m spacy link "
                "en_core_web_md en".format(spacy_model_name)
            )

    def put(self):
        args = self.reqparse.parse_args()
        # for i in args['text']:
        #     print('RECEIVED: ', i)
        print(args["text"], args["entities"], args["params"])
        root = Path(project_dir)
        if args["entities"]:
            nlp_blank = spacy.blank('en')
            with open(os.path.join(root, 'ner/data/data.iob'), 'w') as fout:
                for example, example_entities in zip(args["text"], args["entities"]):
                    entities = []
                    doc = nlp_blank(example)
                    for ent in example_entities:
                        entities.append((ent.get('start'), ent.get('end'), ent.get('entity')))

                    tags = biluo_tags_from_offsets(doc, entities)
                    tokens = [token.text for token in doc]
                    ner_training = [tok + '|' + tag for tok, tag in zip(tokens, tags)]
                    fout.write(' '.join(ner_training) + '\n')

        project_assets(root)
        project_run(root, "all")
        global nlp
        if nlp is None:
            print('Loading the trained model..')
            nlp = self.load_model(model_path)
        return jsonify({'response': f'NER service is running!'})

    @staticmethod
    def extract_entities(doc: "Doc"):
        entities_extracted = [
            {
                "entity": ent.label_,
                "value": ent.text,
                "start": ent.start_char,
                "confidence": None,
                "end": ent.end_char,
            }
            for ent in doc.ents
        ]
        return entities_extracted

    def get(self):
        args = self.reqparse.parse_args()
        all_extracted = []

        global nlp
        if nlp is None:
            nlp = self.load_model(model_path)

        for text in args["text"]:
            doc = nlp(text)
            all_extracted.append(self.extract_entities(doc))
        return {'entities': all_extracted}


api.add_resource(CustomSpacyNER, '/train', '/predict')

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=9501)
