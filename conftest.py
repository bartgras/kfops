import pytest
from package.kfops.config import ConfigMeta

@pytest.fixture(autouse=True)
def reset_singletons():
    ConfigMeta._instances = {}