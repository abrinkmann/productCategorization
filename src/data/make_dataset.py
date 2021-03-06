# -*- coding: utf-8 -*-
import json
import os

import click
import logging
from pathlib import Path
from dotenv import find_dotenv, load_dotenv
import pandas as pd
from sklearn.model_selection import train_test_split
import csv
import pickle

import src.data.unify_datasets as unify


@click.command()
@click.option('--dataset', help='Dataset which you like to preprocess')
def main(dataset):
    """ Runs data processing scripts to turn raw data from (../raw) into
        cleaned data ready to be analyzed (saved in ../processed).
    """
    trigger_load_dataset(dataset)


def trigger_load_dataset(dataset):
    logger = logging.getLogger(__name__)

    # Load dot environment file
    load_dotenv(find_dotenv())
    datasets = os.getenv("DATASETS")

    if dataset not in datasets:
        msg = 'Dataset {} is not defined!'.format(dataset)
        logger.error(msg)
        raise ValueError(msg)
    else:
        load_and_split_dataset(dataset)


def load_and_split_dataset(dataset):
    logger = logging.getLogger(__name__)

    data_dir = os.environ['DATA_DIR']
    data_dir = Path(data_dir)

    path_to_raw_data = data_dir.joinpath('data/raw', dataset)

    dataset_collector = {}

    # Data is already split into train/validation/test + provided in json format
    if dataset == 'wdc_ziqi':
        dict_files = {'train': 'train.json', 'validate': 'validation.json', 'test': 'task2_testset_with_labels.json'}

        for value in dict_files:
            path_to_file = path_to_raw_data.joinpath(dict_files[value])
            df_data = load_line_json(path_to_file)
            dataset_collector[value] = unify.reduce_schema(df_data, dataset)

        logger.info('Dataset {} loaded!'.format(dataset))

    elif os.path.exists(path_to_raw_data.joinpath('split')):
        logger.info('Dataset {} is already split!'.format(dataset))

        for dataset_type in ['train', 'test']:
            train_dataset_name = 'split/{}_data_{}.csv'.format(dataset, dataset_type)
            path_to_raw_dataset = path_to_raw_data.joinpath(train_dataset_name)

            df_raw_data = pd.read_csv(path_to_raw_dataset.absolute(), sep=',', encoding='utf-8', quotechar='"',
                                      quoting=csv.QUOTE_ALL)
            logger.info('Dataset {} loaded!'.format(dataset))

            dataset_collector[dataset_type] = unify.reduce_schema(df_raw_data, dataset)
            logger.info('Dataset {} reduced to target schema!'.format(dataset))
    else:
        logger.info('Dataset {} is not split yet!'.format(dataset))
        dataset_file = '{}_data_raw.csv'.format(dataset)
        path_to_raw_dataset = path_to_raw_data.joinpath(dataset_file)

        df_raw_data = pd.read_csv(path_to_raw_dataset.absolute(), sep=',', encoding='utf-8', quotechar='"',
                                  quoting=csv.QUOTE_ALL)
        logger.info('Dataset {} loaded!'.format(dataset))

        df_data_reduced_schema = unify.reduce_schema(df_raw_data, dataset)
        logger.info('Dataset {} reduced to target schema!'.format(dataset))

        dataset_collector['train'], dataset_collector['test'] = split_dataset(df_data_reduced_schema)

    if dataset != 'wdc_ziqi':
        dataset_collector['train'], dataset_collector['validate'] = split_dataset(dataset_collector['train'])
        logger.info('Dataset {} split into train, validate, test!'.format(dataset))

    for split in dataset_collector:
        persist_dataset(dataset_collector[split], dataset, split)


def load_line_json(path):
    logger = logging.getLogger(__name__)

    df_ds = pd.DataFrame()
    count = 0
    with open(path) as fp:
        while True:
            count += 1
            line = fp.readline()

            if not line:
                logger.info('Read {} lines from {}!'.format(count, path))
                break
            json_object = json.loads(line)
            df_row = pd.DataFrame.from_dict(json_object, orient='index').transpose()
            df_ds = df_ds.append(df_row)

    return df_ds


def split_dataset(df_dataset):
    """Split dataset into train, test and validation set"""
    # split into training and testing set 80:20 (stratify)
    random = int(os.getenv("RANDOM_STATE"))

    # Intermediate Solution: if only one leaf element exists, these elements are added to the trainings set
    # To-Do: Find more sustainable solution
    only_one_root_element = [k for k, v in df_dataset['path_list'].value_counts().items()
                             if df_dataset['path_list'].value_counts()[k] < 2]

    df_one_element = df_dataset[df_dataset['path_list'].isin(only_one_root_element)]
    df_dataset = df_dataset[~df_dataset['path_list'].isin(only_one_root_element)]

    general_columns = ['title', 'description', 'brand', 'category', 'path_list']
    available_columns = [column for column in df_dataset.columns if column in general_columns]

    df_data_train, df_data_test, df_data_train_target, df_data_test_target = train_test_split(
        df_dataset, df_dataset[available_columns], test_size=0.2,
        random_state=random, shuffle=True, stratify=df_dataset[['path_list']])

    df_data_train = pd.concat([df_data_train, df_one_element[available_columns]])

    return df_data_train, df_data_test


def persist_dataset(df_dataset, dataset, split_name):
    logger = logging.getLogger(__name__)
    data_dir = os.environ['DATA_DIR']
    data_dir = Path(data_dir)
    relative_path = 'data/processed/{}/split/raw/{}_data_{}.pkl'.format(dataset, split_name, dataset)
    file_path = data_dir.joinpath(relative_path)

    # Create new path if it does not exist yet!
    if not os.path.exists(file_path):
        logger.info('Path {} does not exist!'.format(file_path))
        path_parts = relative_path.split('/')
        path_parts = path_parts[:-1]
        file_path = data_dir
        for part in path_parts:
            file_path = file_path.joinpath(part)
            if not os.path.exists(file_path):
                os.mkdir(file_path)
                logger.info('Path {} created!'.format(file_path))
        file_path = file_path.joinpath('{}_data_{}.pkl'.format(split_name, dataset))

    with open(file_path, 'wb') as f:
        pickle.dump(df_dataset, f)
        logger.info('{} Split of Dataset saved at {}!'.format(split_name, dataset, file_path))


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    main()
