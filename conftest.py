import os

def pytest_runtest_setup(item):
    # put in config
    cache_file = 'country_data_cache.json'
    try:
        os.unlink(cache_file)
    except Exception:
        pass