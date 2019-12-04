#!/usr/bin/env python

import argparse
import json
import sys

from aggregation.aggregation_processor import process_aggregation_request


def get_country_data():
    """Retrieve aggregated stats by aggregation type, metric, and region
    """

    parser = argparse.ArgumentParser(
        description='Retrieve aggregated stats by aggregation type, metric, and region.',
    )
    parser.add_argument(
        '--aggregation',
        required=True,
        choices=[
            'avg',
            'count',
            'max',
            'min',
            'sum',
        ],
        help='Aggregation type',
    )
    parser.add_argument(
        '--field',
        required=True,
        choices=[
            'area',
            'borders',
            'countries',
            'currencies',
            'gini',
            'languages',
            'latlng',
            'population',
        ],
        help='Metric to aggregate',
    )
    parser.add_argument(
        '--by',
        required=True,
        choices=[
            'region',
            'subregion',
        ],
        help='Field to group aggregates by',
    )

    args = parser.parse_args()
    params = {
        'aggregation': args.aggregation,
        'field': args.field,
        'by': args.by,
    }
    return process_aggregation_request(params)


if __name__ == '__main__':
    response, error = get_country_data()
    if error:
        sys.exit(error)
    else:
        print(json.dumps(response, indent=2))
