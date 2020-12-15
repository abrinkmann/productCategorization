from transformers import BertTokenizerFast, BertForSequenceClassification, RobertaTokenizerFast, \
    RobertaForSequenceClassification
from src.models.transformers.custom_transformers.roberta_for_hierarchical_classification_rnn import \
    RobertaForHierarchicalClassificationRNN
from src.models.transformers.custom_transformers.roberta_for_hierarchical_classification_hierarchy import \
    RobertaForHierarchicalClassificationHierarchy


#To-Do: Refactor code at some point --> Interface is not clear anymore

def provide_model_and_tokenizer(name, pretrained_model_or_path, num_labels=2, config=None):
    if name == 'transformers-base-uncased':
        return bert_base_uncased(num_labels)
    elif name == 'transformers-large-uncased':
        return  bert_large_uncased(num_labels)
    elif name == 'roberta-base':
        return roberta_base(num_labels)
    elif name == 'roberta-base-hierarchy-rnn':
        return roberta_base_hierarchy_rnn(config, pretrained_model_or_path)
    elif name == 'roberta-base-hierarchy-exploit':
        return roberta_base_hierarchy_exploit(config)

    raise ValueError('Unknown model name: {}!'.format(name))

def provide_tokenizer(name):
    if name == 'roberta-base':
        return roberta_base_tokenizer()

    raise ValueError('Unknown model name: {}!'.format(name))

def bert_base_uncased(num_labels):
    tokenizer = BertTokenizerFast.from_pretrained('transformers-base-uncased')
    model = BertForSequenceClassification.from_pretrained("transformers-base-uncased",num_labels=num_labels)

    return tokenizer, model

def bert_large_uncased(num_labels):
    tokenizer = BertTokenizerFast.from_pretrained('transformers-large-uncased')
    model = BertForSequenceClassification.from_pretrained("transformers-large-uncased",num_labels=num_labels)

    return tokenizer, model

def roberta_base(num_labels):
    tokenizer = RobertaTokenizerFast.from_pretrained('roberta-base')
    model = RobertaForSequenceClassification.from_pretrained('roberta-base', num_labels=num_labels)

    return tokenizer, model

def roberta_base_hierarchy_rnn(config, pretrained_model_or_path):
    tokenizer = RobertaTokenizerFast.from_pretrained('roberta-base')
    model = RobertaForHierarchicalClassificationRNN.from_pretrained(pretrained_model_or_path, config=config)

    return tokenizer, model

#def roberta_base_hierarchy_att_rnn(num_labels, pretrained_model_or_path):
#    tokenizer = RobertaTokenizerFast.from_pretrained('roberta-base')
#    model = RobertaForHierarchicalClassificationAttRNN.from_pretrained(pretrained_model_or_path, num_labels=num_labels)
#    return tokenizer, model

def roberta_base_tokenizer():
    tokenizer = RobertaTokenizerFast.from_pretrained('roberta-base')

    return tokenizer

def roberta_base_hierarchy_exploit(config):
    tokenizer = RobertaTokenizerFast.from_pretrained('roberta-base')
    model = RobertaForHierarchicalClassificationHierarchy\
        .from_pretrained('roberta-base', config=config)

    return tokenizer, model
