import csv
import gzip
import logging
import copy
from multiprocessing import Process, Semaphore, Value
import time
from os import listdir
from pathlib import Path
import re
import pandas as pd

import click

from src.data.preprocessing import preprocess
from src.data.wdc_ziqi.extract_hosts import extract_host


@click.command()
@click.option('--file_dir', help='Path to dir containing files with products')
@click.option('--output_dir', help='Path to output_dir')
@click.option('--host_path', help='Path to file containing hosts')
@click.option('--worker', help='Number of workers', type=int)
def main(file_dir, output_dir, host_path, worker):
    logger = logging.getLogger(__name__)
    # Load searched hosts
    hosts = load_hosts(host_path)

    sema = Semaphore(worker)
    processed_products = Value('i', 0)
    all_processes = []
    counter = 1

    for file in listdir(file_dir):
        if '.gz' in file:
            input_file = '{}/{}'.format(file_dir, file)
            output_file = '{}/{}.txt'.format(output_dir, file.split('.')[-2])

            # Check if output file does not exist!
            if not Path(output_file).is_file():
                sema.acquire()
                process = Process(target=extract_products, args=(input_file, output_file, hosts, sema, processed_products,))
                all_processes.append(process)
                process.start()
                logger.info('Started {} processes!'.format(counter))

            # Join finished processes
            for p in all_processes:
                if p.exitcode != None:
                    if p.exitcode == 0 or p.exitcode < 0:
                        p.join()
                        p.close()
                        all_processes.remove(p)
                        logger.info('Processed {} products!'.format(processed_products.value))

            counter += 1

    logger.info('Wait for all processes to finish!')
    for p in all_processes:
        p.join()
        p.close()
        all_processes.remove(p)
        logger.info('Processed {} products!'.format(processed_products.value))



def extract_products(file_path, output_path, hosts, sema, processed_products):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    categories = set()
    breadcrumbs = set()
    breadcrumbLists = set()

    collected_products = []
    counter = 0
    product = {'Title': '', 'Description': '', 'Category': '', 'Breadcrumb': '',
               'BreadcrumbList': '', 'Breadcrumb-Predicate': '', 'URL': '', 'Host': ''}
    uri = None
    p = None  # Process for Multithreading

    # Initialize output file
    with open(output_path, 'w') as out_f:
        line = 'Title;Description;Category;Breadcrumb;BreadcrumbList;Breadcrumb-Predicate;URL;Host\n'
        out_f.write(line)

    logger.info('Initialize output file {}!'.format(output_path))

    with gzip.open(file_path, 'rt', encoding='utf-8') as f:

        for i, line in enumerate(f):
            reader = csv.reader([line], delimiter=' ', quotechar='"')
            try:
                for r in reader:
                    if len(r) > 4:

                        if not (uri is None) and r[3] != uri and '.' in uri:

                            if len(product['Title']) > 0 and (len(product['Category']) > 0 or
                                                              len(product['Breadcrumb']) > 0 or
                                                              len(product['Description']) > 0 or  # Relax constraints
                                                              len(product['BreadcrumbList']) > 0):

                                collected_products.append(copy.deepcopy(product))
                                # Initialize product dict
                                product = {key: '' for key in product}
                                counter += 1

                                if counter % 10000 == 0:
                                    p = parallel_write(p, collected_products, output_path)
                                    collected_products = []
                                    logger.info('Written {} product names to disc.'.format(counter))

                                    for value in categories:
                                        logger.info('Category value: {}'.format(value))

                                    for value in breadcrumbs:
                                        logger.info('Breadcrumbs value: {}'.format(value))

                                    for value in breadcrumbLists:
                                        logger.info('Breadcrumblists value: {}'.format(value))

                        #Update URI
                        uri = r[3]

                        # Check if we look for the given host
                        searched_host = True
                        if hosts is not None:
                            searched_host = False
                            for host in hosts:
                                if host in r[3]:
                                    searched_host = True
                                    break

                        if searched_host:
                            product['URL'] = r[3]
                            if r[1] == '<http://schema.org/Product/name>' and '@en' in r[2]:
                                prep_value = preprocess_value(r[2])
                                if len(prep_value) > 0 and prep_value != 'null':
                                    product['Title'] = prep_value

                            elif r[1] == '<http://schema.org/Product/description>':
                                prep_value = preprocess_value(r[2])
                                exclude_values = ['description', 'a href', 'various', 'share', '0', 'more']
                                if len(prep_value) > 0 and prep_value != 'null' and prep_value not in exclude_values:
                                    product['Description'] = prep_value

                            # elif 'breadcrumblist' in r[2].lower():
                            #    node = r[0]
                            #    node_relevant = True
                            # logger.info(r)

                            elif 'category' in r[1].lower():
                                prep_value = preprocess_value(r[2])
                                if len(prep_value) > 0 and prep_value != 'null' and prep_value != 'more section not available':
                                    if prep_value not in product['Category']:
                                        product['Category'] = '{} {}'.format(product['Category'], prep_value).lstrip()
                                        categories.add(r[1])

                            elif r[1] == '<http://schema.org/Product/breadcrumb>':
                                if '_:node' in r[2]:
                                    pass
                                    # logger.info(r)
                                else:
                                    prep_value = preprocess_value(r[2])
                                    prep_value = re.sub(r"^home", '', prep_value).strip()
                                    if len(prep_value) > 0 and prep_value != 'null':
                                        if prep_value not in product['Breadcrumb']:
                                            product['Breadcrumb'] = '{} {}'.format(product['Breadcrumb'],
                                                                                   prep_value).lstrip()
                                            product['Breadcrumb-Predicate'] = '{} {}'.format(
                                                product['Breadcrumb-Predicate'],
                                                r[1]).lstrip()
                                            breadcrumbs.add(r[1])

                            elif 'breadcrumblist' in r[1].lower():
                                if '_:node' in r[2]:
                                    node = r[2]
                                    node_relevant = True
                                # logger.info(r)
                                else:
                                    prep_value = preprocess_value(r[2])
                                    prep_value = re.sub(r"^home", '', prep_value).strip()
                                    if len(prep_value) > 0 and prep_value != 'null':
                                        product['BreadcrumbList'] = '{} {}'.format(product['BreadcrumbList'],
                                                                                   prep_value).lstrip()
                                        breadcrumbLists.add(r[1])

                            elif 'breadcrumb' in r[1].lower():
                                if r[1] != '<http://schema.org/Breadcrumb/url>' and r[1] != '<http://schema.org/Breadcrumb/child>':
                                    prep_value = preprocess_value(r[2])
                                    prep_value = re.sub(r"^home", '', prep_value)
                                    if len(prep_value) > 0 and prep_value != 'null':
                                        if prep_value not in product['Breadcrumb']:
                                            product['Breadcrumb'] = '{} {}'.format(product['Breadcrumb'],
                                                                                   prep_value).lstrip()
                                            product['Breadcrumb-Predicate'] = '{} {}'.format(
                                                product['Breadcrumb-Predicate'], r[1]).lstrip()
                                            breadcrumbs.add(r[1])

            except csv.Error as e:
                logger.error(e)

    p = parallel_write(p, collected_products, output_path)
    logger.info('Written offers to disc.')
    p.join()

    for value in categories:
        logger.info('Category value: {}'.format(value))

    for value in breadcrumbs:
        logger.info('Breadcrumbs value: {}'.format(value))

    for value in breadcrumbLists:
        logger.info('Breadcrumblists value: {}'.format(value))

    # Share info about processed products -1: Don't count header row
    processed_products.value = processed_products.value + counter
    # Release Sema so that new processes can start!
    sema.release()




def load_hosts(host_path):
    logger = logging.getLogger(__name__)
    if host_path is None:
        logger.info('No host path supplied!')
        logger.info('Will not load any hosts for filtering!')

        return None
    else:
        hosts = []
        counter = 0
        with open(host_path, 'r') as host_file:
            lines = host_file.readlines()
            for line in lines:
                hosts.append(line.strip())
                counter += 1

        logger.info('Loaded {} hosts!'.format(counter))
        return hosts


def parallel_write(p, products, path):
    logger = logging.getLogger(__name__)
    if p is not None:
        start = time.time()
        p.join()
        end = time.time()
        elapsed_time = end - start
        logger.info('Waited for {}'.format(elapsed_time))
    p = Process(target=remove_duplicates_and_write_to_disk, args=(copy.deepcopy(products), path))
    p.start()
    return p

def remove_duplicates_and_write_to_disk(products, path):
    # Convert to pandas df
    logger = logging.getLogger(__name__)
    dict_products = {'Title': [], 'Category': [], 'Breadcrumb': [], 'BreadcrumbList':[], 'Breadcrumb-Predicate': [],
                     'Description':[], 'URL': [], 'Host': []}
    for product in products:
        for key in dict_products:
            if key == 'Host':
                host = extract_host(product['URL'])
                dict_products['Host'].append(host)
            elif key in product:
                dict_products[key].append(product[key])
            else:
                dict_products[key].append('')



    df_products = pd.DataFrame.from_dict(dict_products)
    df_products.sort_values(by=['Category', 'Breadcrumb', 'BreadcrumbList', 'Description'], inplace=True)
    df_products.drop_duplicates(subset=['Title'], inplace=True)

    # Remove hosts based on count
    host_counts = df_products['Host'].value_counts()
    for host, count in host_counts[host_counts > 500].items():
        # Shuffle and choose rows to be dropped
        df_products_to_be_dropped = df_products[df_products['Host'] == host].sample(frac=1)[10:]
        df_products.drop(df_products_to_be_dropped.index, inplace=True)

    df_products.to_csv(path, sep=';', index=False, mode='a', header=False)

    logger.info('Written {} offers to {}!'.format(len(df_products), path))


def preprocess_value(value):
    value = value.split('@')[0]
    value = value.replace('\\n', '').replace('\\t', '').replace('u00a0', '').replace('u00bb', '')
    prep_value = preprocess(value)
    return prep_value


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    main()
