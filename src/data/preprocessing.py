import re

from bs4 import BeautifulSoup
import numpy as np


# stopwords are not removed for classification based on product titles according to findings of Yu, Product title
# classification versus text classification lowercase and ignoring punctuation is default stopwords can be turned on
# in sklearn as well

# for additional steps needed regarding stemming and lemmatizing see KDnuggets article above

# define functions

def replace_separators(text):
    return ' '.join([re.sub(r'-|/|\.', ' ', text), re.sub(r'-|/|\.', '', text)])
    # return " ".join([a, b])


def remove_html(text):
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()


def remove_hyperlinks(text):
    return re.sub(r'((www\.[\S]+)|(https?://[\S]+))', '', text)


def remove_first_and_last_character(text):
    return text[1:-1]


def remove_tags(text):
    text = re.findall('\[(.*?)\]', text)
    text = ' '.join(text)
    return text


def remove_special_characters(text):
    # return re.sub(r"[\(\)\[\]!\?\.\-\"\$\=]", "", text)
    pattern = re.compile('([^\s\w]|_)+', re.UNICODE)
    return pattern.sub('', text)


def remove_whitespace(text):
    text = re.sub(' +', ' ', text)
    return text.strip()


# Exclude for now
# def replace_contractions(text):
#    return contractions.fix(text)

# def denoise_test_data(text):
#    text = remove_html(text)
#    text =  remove_first_and_last_character(text)
#    text = remove_tags_train(text) 
#    text = remove_hyperlinks(text)
#    text = replace_contractions(text)
#    #text = remove_special_characters(text)
#    #text = remove_whitespace(text)
#    #text = text.lower()
#    return text
#
# def denoise_train_data(text):
#    text = remove_html(text)
#    #text =  remove_first_and_last_character(text)
#    #text = remove_tags_train(text)
#    text = remove_hyperlinks(text)
#    text = replace_contractions(text)
#    #text = remove_special_characters(text)
#    #text = remove_whitespace(text)
#    #text = text.lower()
#    return text

def preprocess(s):
    a = s
    # print('s',s)
    if type(s) == float:
        s = str(s)

    if type(s) != str:
        transformed_list = list()
        for title in s:
            # print(s)
            # print()
            transformed_list.append(preprocess(title))
        return np.array(transformed_list)

    s = s.lower()
    s = remove_hyperlinks(s)
    s = remove_html(s)
    # s = replace_contractions(s) - Exclude for now
    s = remove_special_characters(s)
    s = remove_whitespace(s)

    return s
