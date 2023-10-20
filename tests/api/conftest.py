import pytest


@pytest.fixture
def secrets_file(tmp_path):
    name = tmp_path.joinpath("secrets")
    with open(name, "w") as conf:
        conf.write(
            """user1 3c55d3cdc19876dfc8c0bb49da8c927a0ddff26d
            user2 eb6fb35f5fbba6a6e43d3c893ad7a77dc793ceba
            user3 c8a0b250edb2eabd9616b7b05a46e0ad28226fc2
            """
        )
    yield name


@pytest.fixture
def secrets_file_littered_with_empty_lines(tmp_path):
    name = tmp_path.joinpath("secrets")
    with open(name, "w") as conf:
        conf.write(
            """user1 3c55d3cdc19876dfc8c0bb49da8c927a0ddff26d

            user2 eb6fb35f5fbba6a6e43d3c893ad7a77dc793ceba

            user3 c8a0b250edb2eabd9616b7b05a46e0ad28226fc2
            """
        )
    yield name
