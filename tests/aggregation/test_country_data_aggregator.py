import datetime
from functools import partial
import json
from unittest.mock import mock_open, patch

from freezegun import freeze_time
import pytest

from aggregation.country_data_aggregator import (
    aggregate_list,
    append_list,
    append_one,
    CountryDataAggregator,
)


def test_aggregate_list():
    data_set = [
        [1, 1, 1],
        [2, 2, 2],
        [3, 3, 3],
    ]
    results = aggregate_list(sum, data_set)
    assert results == [3, 6, 9]

@pytest.mark.parametrize(
    'length, target, value, expected',
    [
        (2, [], None, [[0], [0]]), # empty list, null value
        (2, [[1], [2]], [3, 4], [[1, 3], [2, 4]]), # populated list
        (2, [[1], [2]], [3], [[1, 3], [2, 0]]), # missing value
    ],
)
def test_append_list(length, target, value, expected):
    append_list(length, target, value)
    assert target == expected

@pytest.mark.parametrize(
    'target, value, expected',
    [
        ([], None, [1]), # empty list, null value
        ([1, 1], 10, [1, 1, 1]), # populated list
    ],
)
def test_append_one(target, value, expected):
    append_one(target, value)
    assert target == expected


@pytest.fixture(scope='module')
def aggregator():
    aggregator = CountryDataAggregator()
    aggregator.country_data_expiry = datetime.datetime.now()
    aggregator.country_data = [
        {'area': 1, 'borders': ['a', 'b', 'c'], 'currencies': ['d', 'e'], 'gini': 11.11, 'latlng': [10.1, 12.2], 'region': 'a', 'subregion': 'aa'},
        {'area': 2, 'borders': ['d', 'e'], 'currencies': ['f'], 'gini': 12.12, 'latlng': [20.2, 22.3], 'region': 'a', 'subregion': 'aa'},
        {'area': 3, 'borders': ['f']},
        {'area': 4, 'borders': ['x'], 'currencies': ['x', 'y'], 'gini': 100.1, 'latlng': [50.1, 62.2], 'region': 'b', 'subregion': 'ba'},
        {'area': 5, 'borders': ['y', 'z'], 'currencies': ['z', 'a'], 'gini': 100.2, 'latlng': [70.2, 82.3], 'region': 'b', 'subregion': 'bb'},
    ]
    aggregator.aggregation_request_results = {'a:b:c': 'test'}
    return aggregator

@pytest.fixture(scope='module')
def mock_cache_file():
    with patch('aggregation.country_data_aggregator.os.path.isfile') as mock_isfile:
        mock_isfile.return_value = True
        with patch('builtins.open', mock_open(read_data='{}')) as mock_cache_file:
            yield mock_isfile, mock_cache_file

@pytest.mark.parametrize(
    'aggregation, field, by, expected',
    [
        ('sum', 'area', 'region', {'a': 3, 'b': 9, 'null': 3}), # valid sum aggregation
        ('a', 'b', 'c', 'test'), # aggregation from cached results
    ],
)
def test_aggregator_get_aggregation(mock_cache_file, aggregator, aggregation, field, by, expected):
    params = {
        'aggregation': aggregation,
        'field': field,
        'by': by,
    }
    results = aggregator.get_aggregation(params)
    assert results == expected

def test_aggregator_get_request_key(aggregator):
    params = {
        'aggregation': 'a',
        'field': 'b',
        'by': 'c',
    }
    key = aggregator.get_request_key(params)
    assert key == 'a:b:c'

@pytest.mark.parametrize(
    'field, by, accumulator, expected',
    [
        ('area', 'region', None, {'a': [1, 2], 'null': [3], 'b': [4, 5]}), # accumulate integer values, with nulls
        ('borders', 'subregion', None, {'aa': [3, 2], 'null': [1], 'ba': [1], 'bb': [2]}), # accumulate list counts, with nulls
        ('latlng', 'region', partial(append_list, 2), {'a': [[10.1, 20.2], [12.2, 22.3]], 'null': [[0], [0]], 'b': [[50.1, 70.2], [62.2, 82.3]]}), # accumulate lists, with nulls
    ],
)
def test_aggregator_accumulate_data_sets(aggregator, field, by, accumulator, expected):
    results = aggregator.accumulate_data_sets(field, by, accumulator)
    assert results == expected

@pytest.mark.parametrize(
    'accumulation_results, aggregation_method, aggregator_fnc, expected',
    [
        ({'a': [1, 2], 'null': [3], 'b': [4, 5]}, 'sum', None, {'a': 3, 'b': 9, 'null': 3}), # sum aggregation function
        ({'a': [[10.1, 20.2], [12.2, 22.3]], 'null': [[0], [0]], 'b': [[50.1, 70.2], [62.2, 82.3]]}, 'avg', aggregate_list, {'a': [15.15, 17.25], 'b': [60.15, 72.25], 'null': [0, 0]}), # custom aggregation function
    ],
)
def test_aggregator_aggregate_data_sets(aggregator, accumulation_results, aggregation_method, aggregator_fnc, expected):
    results = aggregator.aggregate_data_sets(accumulation_results, aggregation_method, aggregator_fnc)
    assert results == expected

@pytest.mark.parametrize(
    'country_data, cache_expiry, expected',
    [
        ('something', datetime.datetime.now() + datetime.timedelta(hours=1), False), # not expired
        (None, datetime.datetime.now() + datetime.timedelta(hours=1), True), # null data
        ('something', None, True), # null expiry
        ('something', datetime.datetime.now() - datetime.timedelta(hours=1), True), # expired on expiry
    ],
)
def test_aggregator_is_expired(aggregator, country_data, cache_expiry, expected):
    aggregator.country_data = country_data
    aggregator.country_data_expiry = cache_expiry
    assert aggregator.is_expired() == expected

@freeze_time('2019-09-20 00:00:00')
def test_aggregator_store_data(mock_cache_file, aggregator):
    country_data = [{'a': 'b'}, {'c': 'd'}]
    aggregator.store_data(country_data, 60)
    assert aggregator.country_data == country_data
    assert aggregator.country_data_expiry == datetime.datetime.now() + datetime.timedelta(seconds=60)
    assert aggregator.aggregation_request_results == {}

def test_aggregator_write_cache(mock_cache_file, aggregator):
    expiry = datetime.datetime.now()
    aggregator.country_data = {'a': 'b'}
    aggregator.country_data_expiry = expiry
    aggregator.aggregation_request_results = {'c': 'd'}
    aggregator.write_cache()

    cache_data = {
        'country_data': aggregator.country_data,
        'country_data_expiry': aggregator.country_data_expiry.strftime('%Y-%m-%d %H:%M:%S'),
        'aggregation_request_results': aggregator.aggregation_request_results,
    }
    mock_file = mock_cache_file[1]
    handle = mock_file()
    handle.write.assert_called_with(json.dumps(cache_data))
