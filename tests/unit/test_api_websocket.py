import aws_cdk as core
import pytest
import aws_cdk.assertions as assertions

from hello_cdk.api_websocket import ApiWebsocketStack

# example tests. To run these tests, uncomment this file along with the example
# resource in hello_cdk/api_websocket.py
def test_sqs_queue_created():
    app = core.App()
    stack = ApiWebsocketStack(app, "ApiWebsocketStack")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#
@pytest.fixture()
def test_cnf_api(stack):
    app = core.App()
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties(("AWS::ApiGatewayV2::Api", {
        "Name": "ApiGatewaysocket",
        "ProtocolType": "WEBSOCKET",
        "RouteSelectionExpression": "$request.body.action"
    }))