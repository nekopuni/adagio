from setuptools import setup

setup(name='adagio',
      version='0.0.1',
      description='Financial backtest module using Quandl database',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'License :: OSI Approved :: MIT License',
          'Programming Language :: Python :: 3.5',
          'Topic :: Office/Business :: Financial :: Investment',
      ],
      keywords='finance backtest Quandl investment',
      url='https://github.com/thoriuchi0531/adagio',
      author='thoriuchi0531',
      author_email='thoriuchi0531@gmail.com',
      license='MIT',
      packages=['adagio'],
      install_requires=[
          'numpy',
          'pandas',
          'quandl',
          'arctic',
      ],
      zip_safe=False,
      include_package_data=True,
      python_requires='>=3.5',
      test_suite='nose.collector',
      tests_require=['nose'])
