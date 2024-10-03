import aws_cdk as core
import pytest
import aws_cdk.assertions as assertions

from hello_cdk.api_websocket import ApiWebsocketStack




def test_lambda_connect_function():
    app = core.App()
    stack = ApiWebsocketStack(app, "ApiWebsocketStack")
    template = assertions.Template.from_stack(stack)
    # Check that the Lambda function is created with the expected properties
    template.has_resource_properties("AWS::Lambda::Function", {
        "Handler": "connect.handler",
        "Runtime": "python3.8",
        "Timeout": 100,
        "MemorySize": 1024
    })

def test_lambda_disconnect_function():
    app = core.App()
    stack = ApiWebsocketStack(app, "ApiWebsocketStack")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::Lambda::Function", {
        "Handler": "disconnect.handler",
        "Runtime": "python3.8",
        "Timeout": 100,
        "MemorySize": 1024

    })



