import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import time
import torch
from transformers import T5ForConditionalGeneration,T5Tokenizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline
import random
import spacy
import zipfile
import os
import json
from sense2vec import Sense2Vec
import requests
from collections import OrderedDict
import string
import pke
import nltk
import numpy 
import yake
from nltk import FreqDist
nltk.download('brown', quiet=True, force=True)
nltk.download('stopwords', quiet=True, force=True)
nltk.download('popular', quiet=True, force=True)
from nltk.corpus import stopwords
from nltk.corpus import brown
from similarity.normalized_levenshtein import NormalizedLevenshtein
from nltk.tokenize import sent_tokenize
from flashtext import KeywordProcessor
# from Questgen.encoding.encoding import beam_search_decoding
# from Questgen.mcq.mcq import tokenize_sentences
# from Questgen.mcq.mcq import get_keywords
# from Questgen.mcq.mcq import get_sentences_for_keyword
# from Questgen.mcq.mcq import generate_questions_mcq
# from Questgen.mcq.mcq import generate_normal_questions
import time
import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import time
import torch
from transformers import T5ForConditionalGeneration,T5Tokenizer
import random
import spacy
import zipfile
import os
import json
from sense2vec import Sense2Vec
import requests
from collections import OrderedDict
import string
import pke
import nltk
from nltk import FreqDist
nltk.download('brown')
nltk.download('stopwords')
nltk.download('popular')
from nltk.corpus import stopwords
from nltk.corpus import brown
# from similarity.normalized_levenshtein import NormalizedLevenshtein
from nltk.tokenize import sent_tokenize
# from flashtext import KeywordProcessor

def beam_search_decoding (inp_ids,attn_mask,model,tokenizer):
  beam_output = model.generate(input_ids=inp_ids,
                                 attention_mask=attn_mask,
                                 max_length=256,
                               num_beams=10,
                               num_return_sequences=3,
                               no_repeat_ngram_size=2,
                               early_stopping=True
                               )
  Questions = [tokenizer.decode(out, skip_special_tokens=True, clean_up_tokenization_spaces=True) for out in
               beam_output]
  return [Question.strip().capitalize() for Question in Questions]



def MCQs_available(word,s2v):
    word = word.replace(" ", "_")
    sense = s2v.get_best_sense(word)
    if sense is not None:
        return True
    else:
        return False


def edits(word):
    "All edits that are one edit away from `word`."
    letters    = 'abcdefghijklmnopqrstuvwxyz '+string.punctuation
    splits     = [(word[:i], word[i:])    for i in range(len(word) + 1)]
    deletes    = [L + R[1:]               for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R)>1]
    replaces   = [L + c + R[1:]           for L, R in splits if R for c in letters]
    inserts    = [L + c + R               for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)


def sense2vec_get_words(word,s2v):
    output = []

    word_preprocessed =  word.translate(word.maketrans("","", string.punctuation))
    word_preprocessed = word_preprocessed.lower()

    word_edits = edits(word_preprocessed)

    word = word.replace(" ", "_")

    sense = s2v.get_best_sense(word)
    most_similar = s2v.most_similar(sense, n=15)

    compare_list = [word_preprocessed]
    for each_word in most_similar:
        append_word = each_word[0].split("|")[0].replace("_", " ")
        append_word = append_word.strip()
        append_word_processed = append_word.lower()
        append_word_processed = append_word_processed.translate(append_word_processed.maketrans("","", string.punctuation))
        if append_word_processed not in compare_list and word_preprocessed not in append_word_processed and append_word_processed not in word_edits:
            output.append(append_word.title())
            compare_list.append(append_word_processed)


    out = list(OrderedDict.fromkeys(output))

    return out

def get_options(answer,s2v):
    distractors =[]

    try:
        distractors = sense2vec_get_words(answer,s2v)
        if len(distractors) > 0:
            print(" Sense2vec_distractors successful for word : ", answer)
            return distractors,"sense2vec"
    except:
        print (" Sense2vec_distractors failed for word : ",answer)


    return distractors,"None"

def tokenize_sentences(text):
    sentences = [sent_tokenize(text)]
    sentences = [y for x in sentences for y in x]
    # Remove any short sentences less than 20 letters.
    sentences = [sentence.strip() for sentence in sentences if len(sentence) > 5]
    return sentences


def get_sentences_for_keyword(keywords, sentences):
    keyword_processor = KeywordProcessor()
    keyword_sentences = {}
    for word in keywords:
        word = word.strip()
        keyword_sentences[word] = []
        keyword_processor.add_keyword(word)
    for sentence in sentences:
        keywords_found = keyword_processor.extract_keywords(sentence)
        for key in keywords_found:
            keyword_sentences[key].append(sentence)

    for key in keyword_sentences.keys():
        values = keyword_sentences[key]
        values = sorted(values, key=len, reverse=True)
        keyword_sentences[key] = values

    delete_keys = []
    for k in keyword_sentences.keys():
        if len(keyword_sentences[k]) == 0:
            delete_keys.append(k)
    for del_key in delete_keys:
        del keyword_sentences[del_key]

    return keyword_sentences


def is_far(words_list,currentword,thresh,normalized_levenshtein):
    threshold = thresh
    score_list =[]
    for word in words_list:
        score_list.append(normalized_levenshtein.distance(word.lower(),currentword.lower()))
    if min(score_list)>=threshold:
        return True
    else:
        return False

def filter_phrases(phrase_keys,max,normalized_levenshtein ):
    filtered_phrases =[]
    if len(phrase_keys)>0:
        filtered_phrases.append(phrase_keys[0])
        for ph in phrase_keys[1:]:
            if is_far(filtered_phrases,ph,0.7,normalized_levenshtein ):
                filtered_phrases.append(ph)
            if len(filtered_phrases)>=max:
                break
    return filtered_phrases


def get_nouns_multipartite(text):
    # out = []

    # extractor = pke.unsupervised.MultipartiteRank()
    # extractor.load_document(input=text, language='en')
    # pos = {'PROPN', 'NOUN'}
    # stoplist = list(string.punctuation)
    # stoplist += stopwords.words('english')
    # extractor.candidate_selection(pos=pos)
    # # 4. build the Multipartite graph and rank candidates using random walk,
    # #    alpha controls the weight adjustment mechanism, see TopicRank for
    # #    threshold/method parameters.
    # try:
    #     extractor.candidate_weighting(alpha=1.1,
    #                                   threshold=0.75,
    #                                   method='average')
    # except:
    #     return out

    # keyphrases = extractor.get_n_best(n=10)

    # for key in keyphrases:
    #     out.append(key[0])

    # nlp = spacy.load("en_core_web_sm")
    # labels = nlp(text)

    # for i in (labels.ents):
    #     out.append(str(i))
    nlp = spacy.load('en_core_web_sm')
    doc = nlp(text)
    ner_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")
    # Extract named entities using spaCy
    spacy_entities = [ent.text for ent in doc.ents]
    print(f"\n\nSpacy Entities: {spacy_entities}\n\n")
    # Extract named entities using BERT-based NER
    bert_entities = [entity['word'] for entity in ner_pipeline(text)]
    print(f"BERT Entities: {bert_entities}\n\n")
    # Combine both NER results and remove duplicates
    entities = list(set(spacy_entities))

    # Extract nouns and verbs using spaCy
    nouns = [chunk.text for chunk in doc.noun_chunks]
    verbs = [token.lemma_ for token in doc if token.pos_ == 'VERB']
    print(f"Spacy Nouns: {nouns}\n\n")
    print(f"Spacy Verbs: {verbs}\n\n")
    
    # Use YAKE for keyphrase extraction
    yake_extractor = yake.KeywordExtractor()
    yake_keywords = yake_extractor.extract_keywords(text)
    yake_keywords = [kw[0] for kw in yake_keywords]
    print(f"Yake: {yake_keywords}\n\n")
    # Combine all keywords and remove duplicates
    combined_keywords = list(set(entities + nouns + verbs + yake_keywords))
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(combined_keywords)
    similarity_matrix = cosine_similarity(tfidf_matrix)
    clusters = []

    similarity_threshold = 0.45

    for idx, word in enumerate(combined_keywords):
        added_to_cluster = False
        for cluster in clusters:
            # Check if the word is similar to any word in the existing cluster
            if any(similarity_matrix[idx, other_idx] > similarity_threshold for other_idx in cluster):
                cluster.append(idx)
                added_to_cluster = True
                break
        if not added_to_cluster:
            clusters.append([idx])

    # Step 4: Select representative words from each cluster
    representative_words = [combined_keywords[cluster[0]] for cluster in clusters]

    # Print the representative words
    # print("Keywords after removing similar words: ", representative_words)
    # return combined_keywords

    return representative_words


def get_phrases(doc):
    phrases={}
    for np in doc.noun_chunks:
        phrase =np.text
        len_phrase = len(phrase.split())
        if len_phrase > 1:
            if phrase not in phrases:
                phrases[phrase]=1
            else:
                phrases[phrase]=phrases[phrase]+1

    phrase_keys=list(phrases.keys())
    phrase_keys = sorted(phrase_keys, key= lambda x: len(x),reverse=True)
    phrase_keys=phrase_keys[:50]
    return phrase_keys



def get_keywords(nlp,text,max_keywords,s2v,fdist,normalized_levenshtein,no_of_sentences):
    doc = nlp(text)
    max_keywords = int(max_keywords)

    keywords = get_nouns_multipartite(text)
    keywords = sorted(keywords, key=lambda x: fdist[x])
    keywords = filter_phrases(keywords, max_keywords,normalized_levenshtein )

    phrase_keys = get_phrases(doc)
    filtered_phrases = filter_phrases(phrase_keys, max_keywords,normalized_levenshtein )

    total_phrases = keywords + filtered_phrases

    total_phrases_filtered = filter_phrases(total_phrases, min(max_keywords, 2*no_of_sentences),normalized_levenshtein )


    answers = []
    for answer in total_phrases_filtered:
        if answer not in answers and MCQs_available(answer,s2v):
            answers.append(answer)

    answers = answers[:max_keywords]
    return answers


def generate_questions_mcq(keyword_sent_mapping,device,tokenizer,model,sense2vec,normalized_levenshtein):
    batch_text = []
    answers = keyword_sent_mapping.keys()
    for answer in answers:
        txt = keyword_sent_mapping[answer]
        context = "context: " + txt
        text = context + " " + "answer: " + answer + " </s>"
        batch_text.append(text)

    encoding = tokenizer.batch_encode_plus(batch_text, pad_to_max_length=True, return_tensors="pt")


    print ("Running model for generation")
    input_ids, attention_masks = encoding["input_ids"].to(device), encoding["attention_mask"].to(device)

    with torch.no_grad():
        outs = model.generate(input_ids=input_ids,
                              attention_mask=attention_masks,
                              max_length=150)

    output_array ={}
    output_array["questions"] =[]
#     print(outs)
    for index, val in enumerate(answers):
        individual_question ={}
        out = outs[index, :]
        dec = tokenizer.decode(out, skip_special_tokens=True, clean_up_tokenization_spaces=True)

        Question = dec.replace("question:", "")
        Question = Question.strip()
        individual_question["question_statement"] = Question
        individual_question["question_type"] = "MCQ"
        individual_question["answer"] = val
        individual_question["id"] = index+1
        individual_question["options"], individual_question["options_algorithm"] = get_options(val, sense2vec)

        individual_question["options"] =  filter_phrases(individual_question["options"], 10,normalized_levenshtein)
        index = 3
        individual_question["extra_options"]= individual_question["options"][index:]
        individual_question["options"] = individual_question["options"][:index]
        individual_question["context"] = keyword_sent_mapping[val]
     
        if len(individual_question["options"])>0:
            output_array["questions"].append(individual_question)

    return output_array

def generate_normal_questions(keyword_sent_mapping,device,tokenizer,model):  #for normal one word questions
    batch_text = []
    answers = keyword_sent_mapping.keys()
    for answer in answers:
        txt = keyword_sent_mapping[answer]
        context = "context: " + txt
        text = context + " " + "answer: " + answer + " </s>"
        batch_text.append(text)

    encoding = tokenizer.batch_encode_plus(batch_text, pad_to_max_length=True, return_tensors="pt")


    print ("Running model for generation")
    input_ids, attention_masks = encoding["input_ids"].to(device), encoding["attention_mask"].to(device)

    with torch.no_grad():
        outs = model.generate(input_ids=input_ids,
                              attention_mask=attention_masks,
                              max_length=150)

    output_array ={}
    output_array["questions"] =[]
    
    for index, val in enumerate(answers):
        individual_quest= {}
        out = outs[index, :]
        dec = tokenizer.decode(out, skip_special_tokens=True, clean_up_tokenization_spaces=True)
        
        Question= dec.replace('question:', '')
        Question= Question.strip()

        individual_quest['Question']= Question
        individual_quest['Answer']= val
        individual_quest["id"] = index+1
        individual_quest["context"] = keyword_sent_mapping[val]
        
        output_array["questions"].append(individual_quest)
        
    return output_array

def random_choice():
    a = random.choice([0,1])
    return bool(a)
    
class QGen:
    
    def __init__(self):

        self.tokenizer = T5Tokenizer.from_pretrained('t5-large')
        model = T5ForConditionalGeneration.from_pretrained('Parth/result')
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        # model.eval()
        self.device = device
        self.model = model
        self.nlp = spacy.load('en_core_web_sm')

        self.s2v = Sense2Vec().from_disk('s2v_old')

        self.fdist = FreqDist(brown.words())
        self.normalized_levenshtein = NormalizedLevenshtein()
        self.set_seed(42)
        
    def set_seed(self,seed):
        numpy.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            
    def predict_mcq(self, payload):
        start = time.time()
        inp = {
            "input_text": payload.get("input_text"),
            "max_questions": payload.get("max_questions", 4)
        }

        text = inp['input_text']
        sentences = tokenize_sentences(text)
        joiner = " "
        modified_text = joiner.join(sentences)


        keywords = get_keywords(self.nlp,modified_text,inp['max_questions'],self.s2v,self.fdist,self.normalized_levenshtein,len(sentences) )


        keyword_sentence_mapping = get_sentences_for_keyword(keywords, sentences)

        for k in keyword_sentence_mapping.keys():
            text_snippet = " ".join(keyword_sentence_mapping[k][:3])
            keyword_sentence_mapping[k] = text_snippet

   
        final_output = {}

        if len(keyword_sentence_mapping.keys()) == 0:
            return final_output
        else:
            try:
                generated_questions = generate_questions_mcq(keyword_sentence_mapping,self.device,self.tokenizer,self.model,self.s2v,self.normalized_levenshtein)

            except:
                return final_output
            end = time.time()

            final_output["statement"] = modified_text
            final_output["questions"] = generated_questions["questions"]
            final_output["time_taken"] = end-start
            
            if torch.device=='cuda':
                torch.cuda.empty_cache()
                
            return final_output
    
    def predict_shortq(self, payload):
        inp = {
            "input_text": payload.get("input_text"),
            "max_questions": payload.get("max_questions", 4)
        }

        text = inp['input_text']
        sentences = tokenize_sentences(text)
        joiner = " "
        modified_text = joiner.join(sentences)


        keywords = get_keywords(self.nlp,modified_text,inp['max_questions'],self.s2v,self.fdist,self.normalized_levenshtein,len(sentences) )


        keyword_sentence_mapping = get_sentences_for_keyword(keywords, sentences)
        
        for k in keyword_sentence_mapping.keys():
            text_snippet = " ".join(keyword_sentence_mapping[k][:3])
            keyword_sentence_mapping[k] = text_snippet

        final_output = {}

        if len(keyword_sentence_mapping.keys()) == 0:
            print('ZERO')
            return final_output
        else:
            
            generated_questions = generate_normal_questions(keyword_sentence_mapping,self.device,self.tokenizer,self.model)
            print(generated_questions)

            
        final_output["statement"] = modified_text
        final_output["questions"] = generated_questions["questions"]
        
        if torch.device=='cuda':
            torch.cuda.empty_cache()

        return final_output
            
  
    def paraphrase(self,payload):
        start = time.time()
        inp = {
            "input_text": payload.get("input_text"),
            "max_questions": payload.get("max_questions", 3)
        }

        text = inp['input_text']
        num = inp['max_questions']
        
        self.sentence= text
        self.text= "paraphrase: " + self.sentence + " </s>"

        encoding = self.tokenizer.encode_plus(self.text,pad_to_max_length=True, return_tensors="pt")
        input_ids, attention_masks = encoding["input_ids"].to(self.device), encoding["attention_mask"].to(self.device)

        beam_outputs = self.model.generate(
            input_ids=input_ids,
            attention_mask=attention_masks,
            max_length= 50,
            num_beams=50,
            num_return_sequences=num,
            no_repeat_ngram_size=2,
            early_stopping=True
            )

#         print ("\nOriginal Question ::")
#         print (text)
#         print ("\n")
#         print ("Paraphrased Questions :: ")
        final_outputs =[]
        for beam_output in beam_outputs:
            sent = self.tokenizer.decode(beam_output, skip_special_tokens=True,clean_up_tokenization_spaces=True)
            if sent.lower() != self.sentence.lower() and sent not in final_outputs:
                final_outputs.append(sent)
        
        output= {}
        output['Question']= text
        output['Count']= num
        output['Paraphrased Questions']= final_outputs
        
        for i, final_output in enumerate(final_outputs):
            print("{}: {}".format(i, final_output))

        if torch.device=='cuda':
            torch.cuda.empty_cache()
        
        return output


class BoolQGen:
       
    def __init__(self):
        self.tokenizer = T5Tokenizer.from_pretrained('t5-base')
        model = T5ForConditionalGeneration.from_pretrained('ramsrigouthamg/t5_boolean_questions')
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        # model.eval()
        self.device = device
        self.model = model
        self.set_seed(42)
        
    def set_seed(self,seed):
        numpy.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    def random_choice(self):
        a = random.choice([0,1])
        return bool(a)
    

    def predict_boolq(self,payload):
        start = time.time()
        inp = {
            "input_text": payload.get("input_text"),
            "max_questions": payload.get("max_questions", 4)
        }

        text = inp['input_text']
        num= inp['max_questions']
        sentences = tokenize_sentences(text)
        joiner = " "
        modified_text = joiner.join(sentences)
        answer = self.random_choice()
        form = "truefalse: %s passage: %s </s>" % (modified_text, answer)

        encoding = self.tokenizer.encode_plus(form, return_tensors="pt")
        input_ids, attention_masks = encoding["input_ids"].to(self.device), encoding["attention_mask"].to(self.device)

        output = beam_search_decoding(input_ids, attention_masks,self.model,self.tokenizer)
        if torch.device=='cuda':
            torch.cuda.empty_cache()
        
        final= {}
        final['Text']= text
        final['Count']= num
        final['Boolean Questions']= output
            
        return final
            
class AnswerPredictor:
          
    def __init__(self):
        self.tokenizer = T5Tokenizer.from_pretrained('t5-large', model_max_length=512)
        model = T5ForConditionalGeneration.from_pretrained('Parth/boolean')
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        # model.eval()
        self.device = device
        self.model = model
        self.set_seed(42)
        
    def set_seed(self,seed):
        numpy.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    def greedy_decoding (inp_ids,attn_mask,model,tokenizer):
        greedy_output = model.generate(input_ids=inp_ids, attention_mask=attn_mask, max_length=256)
        Question =  tokenizer.decode(greedy_output[0], skip_special_tokens=True,clean_up_tokenization_spaces=True)
        return Question.strip().capitalize()

    def predict_answer(self,payload):
        answers = []
        inp = {
                "input_text": payload.get("input_text"),
                "input_question" : payload.get("input_question")
            }
        for ques in payload.get("input_question"):
                
            context = inp["input_text"]
            question = ques
            input = "question: %s <s> context: %s </s>" % (question,context)

            encoding = self.tokenizer.encode_plus(input, return_tensors="pt")
            input_ids, attention_masks = encoding["input_ids"].to(self.device), encoding["attention_mask"].to(self.device)
            greedy_output = self.model.generate(input_ids=input_ids, attention_mask=attention_masks, max_length=256)
            Question =  self.tokenizer.decode(greedy_output[0], skip_special_tokens=True,clean_up_tokenization_spaces=True)
            answers.append(Question.strip().capitalize())

        return answers
