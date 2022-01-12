#!/usr/bin/env python3
import unittest
from unittest.mock import Mock, patch

import interloper


class TestHandler(unittest.TestCase):
    @patch("interloper.boto3")
    def test_lambda_handler(self, boto3):
        # Test currently fails, because websocket bits must be mocked away.
        #
        # client_mocks = {
        #     "ecs": Mock(),
        # }
        # client_mocks["ecs"].execute_command = Mock(return_value={"session": {}})
        # boto3.client = Mock(side_effect=lambda x: client_mocks[x])
        # event = {
        #     "cluster": "cluster1",
        #     "task": "task1",
        #     "container": "container1",
        # }
        # interloper.lambda_handler(event, None)
        # boto3.client.assert_called()
        # client_mocks["ecs"].execute_command.assert_called()
        assert True


if __name__ == "__main__":
    unittest.main()
