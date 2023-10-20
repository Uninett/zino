import pytest

from zino.api.auth import AuthenticationFailure, authenticate, get_challenge, read_users


class TestAuthenticate:
    def test_when_challenge_response_is_ok_should_return_true(self, secrets_file):
        good_response = "b3e9ba156949152c5c6f3334cf86333b1daabfe9"
        assert authenticate(
            "user1",
            response=good_response,
            challenge="a97fbebb3eef2dfcf167645229c0c5fa9e92e3da",
            secrets_file=secrets_file,
        )

    def test_when_challenge_response_is_bad_should_raise_error(self, secrets_file):
        bad_response = "aaa9ba156949152c5c6f3334cf86333b1daabbbb"
        with pytest.raises(AuthenticationFailure):
            assert authenticate(
                "user1",
                response=bad_response,
                challenge="a97fbebb3eef2dfcf167645229c0c5fa9e92e3da",
                secrets_file=secrets_file,
            )

    def test_when_user_does_not_exist_should_raise_error(self, secrets_file):
        with pytest.raises(AuthenticationFailure):
            assert authenticate(
                "nobody",
                response="doesntmatter",
                challenge="doesntmatter",
                secrets_file=secrets_file,
            )

    def test_when_challenge_is_empty_should_raise_error(self, secrets_file):
        """Can be removed when challenge-less auth is supported"""
        with pytest.raises(AuthenticationFailure):
            assert authenticate(
                "user1",
                response="doesntmatter",
                secrets_file=secrets_file,
            )


class TestGetChallenge:
    def test_should_return_unique_challenges(self):
        """Challenge strings are expected to be random.  Once in a million years this could fail because of the
        nature of randomness, but it should also protect against the implementation being changed into something that
        returns a constant value.
        """
        count = 10
        challenges = set(get_challenge() for _ in range(count))
        assert len(challenges) == 10, "same challenge was produced more than once"

    def test_should_return_at_least_40_characters(self):
        assert len(get_challenge()) >= 40


class TestReadUsers:
    def test_result_should_match_input_file(self, secrets_file):
        expected = {
            "user1": "3c55d3cdc19876dfc8c0bb49da8c927a0ddff26d",
            "user2": "eb6fb35f5fbba6a6e43d3c893ad7a77dc793ceba",
            "user3": "c8a0b250edb2eabd9616b7b05a46e0ad28226fc2",
        }
        users = read_users(secrets_file)
        assert users == expected

    def test_should_not_crash_on_empty_lines_in_input(self, secrets_file_littered_with_empty_lines):
        assert read_users(secrets_file_littered_with_empty_lines)
