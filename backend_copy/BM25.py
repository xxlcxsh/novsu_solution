from nltk.util import ngrams
import nltk
import math
from collections import Counter
import numpy as np
from nltk.stem.snowball import SnowballStemmer

stemmer = SnowballStemmer("russian")

N_GRAM_SIZE = 3

def display_search_results(documents, idx_scores, char_limit=100):
    for idx, score in idx_scores:
        print(f'{score:0.2f}: {documents[idx][:char_limit]}')

def query_to_ngrams(query, n_gram_size=N_GRAM_SIZE):
    return documents_to_ngrams([query], n_gram_size=n_gram_size)[0]

def calculate_idf(documents_ngrams):
    ngram_appearance = {}
    for doc_ngrams in documents_ngrams:
        for ngram in set(doc_ngrams):
            if ngram not in ngram_appearance:
                ngram_appearance[ngram] = 0
            ngram_appearance[ngram] += 1
    idf = {}
    N = len(documents_ngrams)
    for ngram, appearance_count in ngram_appearance.items():
        idf[ngram] = np.log((1+N)/(1 + appearance_count))
    return idf

def search_tf_idf(
    documents_ngrams,
    query,
    limit=5,
    n_gram_size=N_GRAM_SIZE,
):
    index = [Counter(doc_ngrams) for doc_ngrams in documents_ngrams]
    idf = calculate_idf(documents_ngrams)
    query = query_to_ngrams(query, n_gram_size)

    match_scores = []
    for ngram_counts in index:
        score = 0
        total_ngrams = sum(ngram_counts.values())
        if total_ngrams == 0:
            continue
        for query_ngram in query:
            tf_score = ngram_counts.get(query_ngram, 0)/total_ngrams
            idf_score = idf.get(query_ngram, 1e-3)
            score += tf_score * idf_score
        match_scores.append(score)

    idx_scores = zip(range(len(documents_ngrams)), match_scores)
    idx_scores = sorted(idx_scores, key=lambda pair: -pair[1])

    return idx_scores[:limit]


def documents_to_ngrams(documents, n_gram_size=N_GRAM_SIZE, progress=False):
    document_ngrams = []
    iterator = documents
    for doc in iterator:
        doc_ngrams = []
        for word in doc.split(' '):
            word_ngrams = ngrams(word, n_gram_size)
            for ngram in word_ngrams:
                doc_ngrams.append(''.join(ngram))
        document_ngrams.append(tuple(doc_ngrams))
    document_ngrams = tuple(document_ngrams)

    return document_ngrams
    
def documents_to_index(documents, n_gram_size=N_GRAM_SIZE):
    documents_preprocessed = [
        preprocess_document(doc) for doc in documents
    ]

    documents_ngrams = documents_to_ngrams(documents_preprocessed, n_gram_size)
    return documents_ngrams

class SearchTFIDF:
    def __init__(self, n_gram_size=N_GRAM_SIZE):
        self.n_gram_size = n_gram_size

        self.documents = None
        self.documents_ngrams = None

    def fit(
        self,
        documents,
    ):
        self.documents = documents

        self.documents_ngrams = documents_to_index(
            documents,
            n_gram_size=self.n_gram_size,
        )

    def search(self, query, limit=5):
        idx_scores = search_tf_idf(
            self.documents_ngrams,
            query,
            limit=limit,
            n_gram_size=self.n_gram_size,
        )
        return idx_scores[:limit]

    def search_and_display(self, query, limit=5):
        idx_scores = self.search(query, limit=limit)
        display_search_results(self.documents, idx_scores)


def stem(word):
    return stemmer.stem(word)

def preprocess_document(document):
    new_doc = ''.join(
        c for c in document if c.isalnum() or c == ' '
    ).lower().strip()
    new_doc = ' '.join([
        stem(word) for word in new_doc.split(' ')
    ])
    return new_doc

def documents_to_words(documents):
    documents_words = tuple([doc.split(' ') for doc in documents])
    documents_words = tuple(documents_words)
    return documents_words

def bm25_documents_to_index(documents):
    documents_preprocessed = [
        preprocess_document(doc) for doc in documents
    ]

    documents_words = documents_to_words(documents_preprocessed)
    return documents_words

def bm25_query_to_wrods(query):
    return bm25_documents_to_index([query])[0]

def idf_bm25(
    number_documents_containing_ngram,
    total_documents,
):
    x = (total_documents - number_documents_containing_ngram + 0.5)/(number_documents_containing_ngram + 0.5)
    return np.log(x + 1)

def tf_bm25(ngram_tf, document_length, average_document_length, k1=1.5, b=0.75, delta=1):
    numerator = ngram_tf*(k1+1)
    denominator = ngram_tf + (k1 * (1 - b + b * document_length/average_document_length))
    return numerator/denominator + delta

def bm25_score(
    ngram_idf,
    ngram_tf,
    document_length,
    average_document_length,
    k1=1.5,
    b=0.75,
):
    numerator = ngram_tf*(k1+1)
    denominator = ngram_tf + (k1 * (1 - b + b * document_length/average_document_length))
    return ngram_idf * tf_bm25(ngram_tf, document_length, average_document_length, k1=k1, b=b)


class SearchBM25:
    def __init__(self):
        self.documents = None
        self.documents_ngrams = None
        self.tf = None
        self.idf = None

    def calculate_tf(self, documents_ngrams):
        tf = [Counter(doc_ngrams) for doc_ngrams in documents_ngrams]

        return tf

    def calculate_idf(self, tf, documents_ngrams):
        idf = {}

        documents_containing = {}

        for doc_tf in tf:
            for ngram in doc_tf.keys():
                if not ngram in documents_containing:
                    documents_containing[ngram] = 0
                documents_containing[ngram] += 1

        for ngram in documents_containing.keys():
            idf[ngram] = idf_bm25(
                number_documents_containing_ngram=documents_containing[ngram],
                total_documents=len(documents_ngrams),
            )
        return idf

    def fit(
        self,
        documents,
    ):
        self.documents = documents

        self.documents_ngrams = bm25_documents_to_index(
            documents,
        )

        self.tf = self.calculate_tf(self.documents_ngrams)
        self.idf = self.calculate_idf(self.tf, self.documents_ngrams)

    def search_bm25(
        self,
        query,
        limit,
        only_documents=None,
    ):
        avg_document_length = sum([
            len(doc) for doc in self.documents_ngrams
        ])/len(self.documents_ngrams)
        query = bm25_query_to_wrods(query)
        indexes = []
        match_scores = []

        document_indexes = range(len(self.tf)) if only_documents is None else only_documents
        for i in document_indexes:
            document_tf = self.tf[i]

            document_length = sum(document_tf.values())
            if document_length == 0:
                continue

            score = 0
            for query_ngram in query:
                ngram_score = bm25_score(
                    self.idf.get(query_ngram, 1e-6),
                    document_tf.get(query_ngram, 1e-6),
                    document_length=document_length,
                    average_document_length=avg_document_length,
                )
                score += ngram_score
            match_scores.append(score)
            indexes.append(i)

        idx_scores = zip(indexes, match_scores)
        idx_scores = sorted(idx_scores, key=lambda pair: -pair[1])
        return idx_scores[:limit]


    def search(self, query, limit=5):
        idx_scores = self.search_bm25(
            query,
            limit=limit,
        )
        return idx_scores[:limit]

    def search_and_display(self, query, limit=5, char_limit=100):
        idx_scores = self.search(query, limit=limit)
        display_search_results(self.documents, idx_scores, char_limit=char_limit)


class TwoStageSearch:
    def __init__(self, n_gram_size=3):
        self.n_gram_size = n_gram_size
        self.documents = None
        self.tfidf_index = None
        self.bm25_index = None

    def fit(self, documents):
        self.documents = documents

        self.tfidf_index = SearchTFIDF(n_gram_size=self.n_gram_size)
        self.tfidf_index.fit(self.documents)

        self.bm25_index = SearchBM25()
        self.bm25_index.fit(self.documents)

    @staticmethod
    def gmean(values):
        # Геометрическое среднее без scipy
        # безопасно обрабатывает любые положительные значения
        product = 1.0
        n = len(values)
        for v in values:
            product *= v
        return product ** (1.0 / n)

    def search(self, query, limit_stage1=100, limit_stage2=5):
        idx_scores_stage1 = self.tfidf_index.search(query, limit=limit_stage1)
        idx_scores_stage1 = [p for p in idx_scores_stage1 if p[1] > 1e-05]
        idx_to_score_stage1 = {idx: score for idx, score in idx_scores_stage1}

        only_document_indexes = list(idx_to_score_stage1.keys())
        idx_scores_stage2 = self.bm25_index.search_bm25(
            query, limit=limit_stage2, only_documents=only_document_indexes
        )

        aggregated_scores = {
            idx: self.gmean([score, idx_to_score_stage1[idx]])
            for idx, score in idx_scores_stage2
        }

        idx_scores = [
            (idx, idx_to_score_stage1[idx], score, aggregated_scores[idx])
            for idx, score in idx_scores_stage2
        ]

        idx_scores = sorted(
            idx_scores,
            key=lambda x: (-round(x[-1], 3), -round(x[-2], 3), -round(x[-3], 3)),
        )
        finally_scores = [[idx, final_sc] for idx, _, _, final_sc in idx_scores]
        return finally_scores
    
def bm25_to_faiss_format(bm25_results, all_payloads):
    return [{"payload": all_payloads[idx], "score": score} for idx, score in bm25_results]

def search_BM25_global(searcher, question, all_payloads ,lim_stage2=5):
    finally_scores = searcher.search(question, limit_stage2=lim_stage2)
    bm25_results = bm25_to_faiss_format(finally_scores, all_payloads)
    return bm25_results
    
