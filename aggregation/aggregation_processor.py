import json
import requests

from aggregation.country_data_aggregator import CountryDataAggregator
from aggregation.validation import validate_aggregation_request


# we could put this in a config
DATA_API_URL = 'XXX'


def process_aggregation_request(params):
    """Retrieve aggregated stats by aggregation type, metric, and region

    Keyword arguments:
    params -- dictionary of aggregation parameters
    """

    # validate request parameters
    validation_results = validate_aggregation_request(params)
    if validation_results.errors:
        # we can humanize the messages here
        return None, json.dumps(validation_results.errors, indent=2)

    # initialize aggregation object
    country_data = CountryDataAggregator()
    # fetch data
    if country_data.is_expired():
        try:
            # for showcasing code, we're not going to use the api url
            import sys
            if 'pytest' in sys.modules:
                response = requests.get(DATA_API_URL, timeout=15)
            else:
                import os
                from unittest.mock import patch
                with patch('requests.get') as mock_get:
                    sample_data_file = os.path.join(os.getcwd(), 'sample_data', 'data.json')
                    with open(sample_data_file, 'r', encoding='utf-8') as f:
                        mock_get.return_value.status_code = 200
                        mock_get.return_value.text = f.read()
                        mock_get.return_value.headers = {}
                    response = requests.get(DATA_API_URL, timeout=15)
            if response.status_code == 200:
                json_data = json.loads(response.text)
                # let's cache the data, use cache control max-age as indicator
                # default to caching data for a day
                seconds = 86400
                cache_control = response.headers.get('Cache-Control')
                if cache_control:
                    parts = cache_control.split(',')
                    for part in parts:
                        if part.strip().startswith('max-age='):
                            _, seconds = part.split('=')
                country_data.store_data(json_data, int(seconds))
            else:
                # we can return a message if necessary
                return None, 'Could not retrieve country data, please try again later.'
        except Exception as e:
            # timeouts and other errors
            # we can break this up if necessary
            return None, 'Could not retrieve country data, please try again later.'

    # process aggregation
    aggregation_results = country_data.get_aggregation(params)

    return aggregation_results, None
