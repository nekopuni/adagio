import unittest

from adagio.utils.quandl import (exchange, year, futures_contract_name,
                                 futures_contract_month, next_fut_ticker,
                                 to_yyyymm)


class TestQuandl(unittest.TestCase):
    def test_exchange(self):
        self.assertEqual(exchange('CME/SPH2018'), 'CME')

    def test_year(self):
        self.assertEqual(year('CME/SPH2018'), 2018)
        self.assertEqual(year('CME/N9H2018'), 2018)

    def test_futures_contract_name(self):
        self.assertEqual(futures_contract_name('CME/SPH2018'), 'SP')
        self.assertEqual(futures_contract_name('CME/N9H2018'), 'N9')

    def test_futures_contract_month(self):
        self.assertEqual(futures_contract_month('CME/SPH2018'), 'H')
        self.assertEqual(futures_contract_month('CME/N9H2018'), 'H')

    def test_next_fut_ticker(self):
        self.assertEqual(next_fut_ticker('CME/SPH2018', ['H', 'M', 'U', 'Z']),
                         'CME/SPM2018')
        self.assertEqual(next_fut_ticker('CME/SPZ2018', ['H', 'M', 'U', 'Z']),
                         'CME/SPH2019')
        self.assertEqual(next_fut_ticker('CME/N9H2018', ['H', 'M', 'U', 'Z']),
                         'CME/N9M2018')
        self.assertEqual(next_fut_ticker('CME/N9Z2018', ['H', 'M', 'U', 'Z']),
                         'CME/N9H2019')
        with self.assertRaises(ValueError):
            next_fut_ticker('CME/N9Z2018', ['H', 'M'])

    def test_to_yyyymm(self):
        self.assertEqual(to_yyyymm('CME/SPH2018'), 201803)
