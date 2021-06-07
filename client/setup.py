from setuptools import setup

setup(name='agent',
      version='1.0.0',
      packages=['agent'],
      entry_points={ 'console_scripts': ['agent = agent.__main__:main'] },
)
