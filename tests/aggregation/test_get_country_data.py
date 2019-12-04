import argparse
import datetime
import json
from unittest.mock import mock_open, patch

from freezegun import freeze_time
import pytest

from aggregation.aggregation_processor import process_aggregation_request
from aggregation.country_data_aggregator import CountryDataAggregator


@pytest.fixture(scope='module')
def mock_args():
    request_args = {
        'aggregation': 'sum',
        'field': 'area',
        'by': 'region',
    }
    yield request_args

@pytest.fixture(scope='module')
def mock_cache_file():
    with patch('builtins.open', mock_open()) as mock_cache_file:
        yield mock_cache_file

def test_process_aggregation_request_valid_request(mock_args, mock_cache_file):
    with patch('aggregation.aggregation_processor.requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = '{}'
        mock_get.return_value.headers = {}

        response, error = process_aggregation_request(mock_args)

    assert error is None
    assert response == {}

@freeze_time('2019-09-20 00:00:00')
def test_process_aggregation_request_valid_request_no_max_age(mock_args, mock_cache_file):
    with patch('aggregation.aggregation_processor.requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = '{}'
        mock_get.return_value.headers = {'Cache-Control': 'a=b'}

        response, error = process_aggregation_request(mock_args)

    assert error is None
    assert response == {}

    expiry = datetime.datetime.now() + datetime.timedelta(seconds=86400)
    cache_data = {
        'country_data': {},
        'country_data_expiry': expiry.strftime('%Y-%m-%d %H:%M:%S'),
        'aggregation_request_results': {"sum:area:region": {}},
    }
    handle = mock_cache_file()
    handle.write.assert_called_with(json.dumps(cache_data))

@freeze_time('2019-09-20 00:00:00')
def test_process_aggregation_request_valid_request_with_max_age(mock_args, mock_cache_file):
    with patch('aggregation.aggregation_processor.requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = '{}'
        mock_get.return_value.headers = {'Cache-Control': 'max-age=60'}

        response, error = process_aggregation_request(mock_args)

    assert error is None
    assert response == {}

    expiry = datetime.datetime.now() + datetime.timedelta(seconds=60)
    cache_data = {
        'country_data': {},
        'country_data_expiry': expiry.strftime('%Y-%m-%d %H:%M:%S'),
        'aggregation_request_results': {"sum:area:region": {}},
    }
    handle = mock_cache_file()
    handle.write.assert_called_with(json.dumps(cache_data))

def test_process_aggregation_request_valid_request_cached_data(mock_args, mock_cache_file):
    with patch('aggregation.country_data_aggregator.os.path.isfile') as mock_isfile:
        mock_isfile.return_value = True
        expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
        read_data = {
            'country_data': {},
            'country_data_expiry': expiry.strftime('%Y-%m-%d %H:%M:%S'),
            'aggregation_request_results': {},
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(read_data))) as mock_cache_file:
            response, error = process_aggregation_request(mock_args)

    assert error is None
    assert response == {}

def test_process_aggregation_request_bad_request():
    params = {
        'aggregation': 'sum',
        'field': 'countries',
        'by': 'region',
    }
    response, error = process_aggregation_request(params)

    assert response is None

    errors_dict = json.loads(error)
    assert len(errors_dict) == 1
    assert errors_dict.get('field') == ['unallowed value countries']

def test_process_aggregation_request_api_error(mock_args, mock_cache_file):
    with patch('aggregation.aggregation_processor.requests.get') as mock_get:
        mock_get.return_value.status_code = 500
        response, error = process_aggregation_request(mock_args)

    assert error == 'Could not retrieve country data, please try again later.'

def test_process_aggregation_request_api_exception(mock_args, mock_cache_file):
    with patch('aggregation.aggregation_processor.requests.get') as mock_get:
        mock_get.side_effect = Exception('test')
        response, error = process_aggregation_request(mock_args)

    assert error == 'Could not retrieve country data, please try again later.'

