#!/usr/bin/env python3.6

from urllib import request
import json
from http.client import HTTPResponse
import glob
import sys
import gzip
import shutil
import os
import logging


def read_exts_list_file_to_criteria(filename):
    file = open(filename, 'r')
    exts_list = file.readlines()
    criteria_list = []
    for ext in exts_list:
        criteria_list.append(ext.rstrip('\n'))
    return criteria_list


def write_criteria_to_exts_list_file(criteria_list, filename):
    file = open(filename, 'w')
    count = len(criteria_list)
    i = 0
    for ext in criteria_list:
        file.write(ext)
        i += 1
        if i < count:
            file.write('\n')
    pass


def exist_vsix_file_to_criteria():
    criteria_list = []
    exist_vsix_list = []
    for filename in glob.glob("*.vsix"):
        filename_split = filename.rstrip('.vsix').split('_')
        criteria_list.append(filename_split[0] + "." + filename_split[1])
        exist_vsix_list.append(filename)
    return criteria_list, exist_vsix_list


def criteria_set_to_list(criteria_set):
    criteria_list = []
    for criteria in criteria_set:
        criteria_list.append({"filterType": 7, "value": criteria})
    return criteria_list


def download_vsix(ext_info_list, exist_vsix_list):
    download_url_template = 'https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{ext_name}/{version}/vspackage'
    for ext_info in ext_info_list:
        publisher = ext_info.get('publisher').get('publisherName')
        ext_name = ext_info.get('extensionName')
        version = ext_info.get('versions')[0].get('version')

        filename = publisher + '_' + ext_name + "_" + version + ".vsix"
        if filename in exist_vsix_list:
            logging.info("%s exists, skip", filename)
            continue
        else:
            for exist_vsix in exist_vsix_list:
                if publisher + '_' + ext_name in exist_vsix:
                    os.remove(exist_vsix)
                    logging.info("Deleted old version of %s", exist_vsix)
                    break

        logging.info("Now downloading %s", filename)
        download_url = download_url_template.format(publisher=publisher, ext_name=ext_name,
                                                    version=version)
        request.urlretrieve(download_url, filename + '.gz')

        with gzip.open(filename + '.gz') as f_in:
            with open(filename, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(filename + '.gz')
    pass


def main():
    exts_query_url = 'https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery'
    req_body = {
        "filters": [
            {
                "criteria": [
                    {"filterType": 8, "value": "Microsoft.VisualStudio.Code"},
                    {"filterType": 12, "value": "4096"}
                ],
                "pageNumber": 1,
                "pageSize": 2,
                "sortBy": 0,
                "sortOrder": 0
            }
        ],
        "assetTypes": [],
        "flags": 914
    }
    ext_list_filename = sys.argv[1]
    criteria_list_from_list = read_exts_list_file_to_criteria(
        ext_list_filename)
    criteria_list_from_vsix_file, exist_vsix_list = exist_vsix_file_to_criteria()
    criteria_set = set()
    criteria_set.update(criteria_list_from_list)
    criteria_set.update(criteria_list_from_vsix_file)
    criteria_list = criteria_set_to_list(criteria_set)
    write_criteria_to_exts_list_file(criteria_set, ext_list_filename)
    req_body.get("filters")[0].get("criteria").extend(criteria_list)
    req_body.get("filters")[0].update({"pageSize": len(criteria_list)})

    req = request.Request(exts_query_url)
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    req.add_header('Accept', 'application/json;api-version=3.0-preview.1')
    resp: HTTPResponse = request.urlopen(
        req, json.dumps(req_body).encode('utf-8'))
    resp_body = json.loads(resp.read().decode('utf-8'))
    download_vsix(resp_body.get('results')[0].get(
        'extensions'), exist_vsix_list)
    pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

