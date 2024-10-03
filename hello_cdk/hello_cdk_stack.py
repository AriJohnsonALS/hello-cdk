from sys import api_version

import aws_cdk
from aws_cdk import (
    # Duration,
    Stack,
    Environment,
    # aws_sqs as sqs,
    aws_apigatewayv2 as apigatewayv2,
    aws_dynamodb as dynamodb,
    aws_lambda, Duration, RemovalPolicy, aws_iam, CfnOutput)
import os
dirname = os.path.dirname(__file__)

from constructs import Construct

class ApiWebsocketStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)



        ''' Create an API resource that supports our Websocket and http API
                - protocol_type --> websocket
                - route_selection_expression --> determines how our route is selected
                
        '''

        cnf_api = apigatewayv2.CfnApi(self, "ApiGatewaysocket",
                              name = "ApiGatewaysocket",
                              protocol_type = "WEBSOCKET",
                              route_selection_expression =  "$request.body.action")


        ''' Stores table of connection IDs, and destroys once the stack is deleted
        '''
        table = dynamodb.Table(self,"ConnectionIDTable",
                       partition_key=dynamodb.Attribute(
                       name="id",
                       type=dynamodb.AttributeType.STRING
                        ),
                       read_capacity = 7,
                       write_capacity = 7,
                       removal_policy= RemovalPolicy.DESTROY,
                       )

    #Lambda Functions

        ''' Lambda Connection
            - code: defines the source code for the lambda function 
                - constructs a path to the lambdas directory relative to the current directory. 
                The use of .. means going up one directory level before entering the lambdas directory.
            -handler: the function will be executed by the handler method defined in the 
                      connect.py file located in the lambdas directory
            -runtime: Our environment is python
        '''
        connect_function = aws_lambda.Function(self, "connect_func",
                                    #load the lambda code
                                      code = aws_lambda.Code.from_asset(os.path.join(dirname, './../lambdas')),
                                      handler = "connect.handler",
                                      runtime = aws_lambda.Runtime.PYTHON_3_8,
                                      timeout = Duration.seconds(100),
                                      memory_size = 1024,
                                    )
        #grants permission to read and write to the table so the lambda can interact freely with the table
        table.grant_read_write_data(connect_function)



        ''' Lambda Disconnection
            - code: defines the source code for the lambda function 
                - constructs a path to the lambdas directory relative to the current directory. 
                The use of .. means going up one directory level before entering the lambdas directory.
            -handler: the function will be executed by the handler method defined in the 
                     disconnect.py file located in the lambdas directory
            -runtime: Our environment is python
            - environment:  Passes the DynamoDB table name as an environment variable to the Lambda function.
                            (This allows the function to access the table dynamically without hardcoding the name)
        '''


        disconnect_function = aws_lambda.Function(self, "disconnect_func",
                                      code=aws_lambda.Code.from_asset(os.path.join(dirname, './../lambdas')),
                                      handler="disconnect.handler",
                                      runtime=aws_lambda.Runtime.PYTHON_3_8,
                                      timeout=Duration.seconds(100),
                                      memory_size=1024,
                                     environment={
                                                "TABLE_NAME": table.table_name
                                                  })
        table.grant_read_write_data(disconnect_function)


        # The "message" function

        ''' Lambda message 
                    - code: defines the source code for the lambda function 
                        - constructs a path to the lambdas directory relative to the current directory. 
                        The use of .. means going up one directory level before entering the lambdas directory.
                    -handler: the function will be executed by the handler method defined in the 
                             send_message.py file located in the lambdas directory
                    -runtime: Our environment is python
                    - environment:  Passes the DynamoDB table name as an environment variable to the Lambda function.
                                    (This allows the function to access the table dynamically without hardcoding the name)
                                    URL - Passes the API Gateway endpoint URL, for if/when the 
                                     Lambda function needs to send messages back to the WebSocket clients.
                                     
                    initial policy grants the lambda permission to manage the websocket connections via the API GW.
                    actions - sending messages to connected clients
                    resources- a random ["*"] - can be specified later 
                '''

        message_function = aws_lambda.Function(self, "message_function",
                                              code=aws_lambda.Code.from_asset(os.path.join(dirname, './../lambdas')),
                                              handler="send_message.handler",
                                              runtime=aws_lambda.Runtime.PYTHON_3_8,
                                               timeout=Duration.seconds(100),
                                               memory_size=1024,
                                               environment={
                                                   #stored variables
                                                   "TABLE_NAME": table.table_name,
                                                   #api backend so that api can send BACK message
                                                   "ENDPOINT": f"https://{cnf_api}.execute-api.{self.region}.amazonaws.com/development",
                                               },


                                               initial_policy= [ aws_iam.PolicyStatement(
                                                   effect=aws_iam.Effect.ALLOW,
                                                   #send messages to the api-gw
                                                   actions = ["excecute-api:ManageConnections"],
                                                   resources = ["*"])
                                               ])


    # Instanitate a "role" for the api gateway to invoke our three lambda functions

        ''' aws_iam.Role - creates a role the APIGW can assume
            assumed_by - role can be assumed by the APIGW and allow the permissions attached to the role
        '''
        role = aws_iam.Role(self, "SelfForRoleApiGwInvokeLambda",
                                role_name="SelfForRoleApiGwInvokeLambda",
                                assumed_by=aws_iam.ServicePrincipal('apigateway.amazonaws.com'))

        ''' add_to_policy- method that adds policy to IAM role
            resources- granting ARN (amazon resource name) of the functions that the API can invoke, useful later for 
                        when certain permissions are restricted
            actions - gives permission to invoke the above lambda functions 
        '''

        role.add_to_policy(aws_iam.PolicyStatement(
            resources=[connect_function.function_arn,
                       disconnect_function.function_arn,
                       message_function.function_arn
                       ],
            actions = ["lambda:InvokeFunction"]
        ))

        table.grant_read_write_data(message_function)



    ## INTEGRATIONS

        ''' Connection Integration
            api_id: reference the correct API we are integrating with
            integration_type "Lambda proxy integration- API gatewat will pass entire request and 
                              expect the function to handle the response
            integration_uri - ARN for the Lambda function, tells apigw how to integrate, and invoke
            credentials_arn - checking if permissions are allowed for this to be invoked
        '''

        connection_integration = apigatewayv2.CfnIntegration(self, "connect_lambda",
                                                             api_id = cnf_api.ref,
                                                             integration_type= "AWS_PROXY",
                                                             #invoke URL for lambda function
                                                             integration_uri= f"arn:aws:apigateway:{self.region}lambda:path/2015-03-31/{connect_function.function_arn}/invocations",
                                                             credentials_arn= role.role_arn)

        disconnect_integration = apigatewayv2.CfnIntegration(self, "disconnect_lambda",
                                                             api_id= cnf_api.ref,
                                                             integration_type="AWS_PROXY",
                                                             integration_uri= f"arn:aws:apigateway:{self.region}lambda:path/2015-03-31/{disconnect_function.function_arn}/invocations",
                                                             credentials_arn=role.role_arn)

        msg_integration = apigatewayv2.CfnIntegration(self, "msg_lambda",
                                                             api_id=cnf_api.ref,
                                                             integration_type="AWS_PROXY",
                                                             integration_uri = f"arn:aws:apigateway:{self.region}lambda:path/2015-03-31/{message_function.function_arn}/invocations",
                                                             credentials_arn=role.role_arn)


    #the routes

        ''' API routes
        - api_id - reference the correct API we are integrating with
        - route_key- the "key" for this route, aws uses $connect and $disconnect and $default, but also used 
                      $sendmessage for this purpose
        - authorization_type - No authorization type needed in this, but could have sometime in the future
        - target - sets the target for the route to the integration you previously defined. It links the
                "$" route to the Lambda function through the specified integration.
            
        '''
        connect_route = apigatewayv2.CfnRoute(self, "connect_route",
                                              api_id= cnf_api.ref,
                                              #api recieves request and routes to lambda function
                                              route_key = "$connect",
                                              authorization_type= "NONE",
                                              target= "integrations/" + connection_integration.ref)

        disconnect_route = apigatewayv2.CfnRoute(self, "disconnect_route",
                                              api_id=cnf_api.ref,
                                              route_key="$disconnect",
                                              authorization_type="NONE",
                                              target="integrations/" + disconnect_integration.ref)

        message_route = apigatewayv2.CfnRoute(self, "message_route",
                                              api_id = cnf_api.ref,
                                              route_key="$sendmessage",
                                              authorization_type="NONE",
                                              target="integrations/" + msg_integration.ref)




        #deploy

        ''' Deployment for the API and its apporopiate API referenced
        '''
        deployment = apigatewayv2.CfnDeployment(self, "deployment",
                                                api_id=cnf_api.ref,)




        # extra staging instances
        ''' development_stage
        defines a stage for your API. A stage is a named reference to a deployment of your API, and it is how clients
         will access your API in different environments
         deployment_id = This links the stage to the specific deployment created earlier, allowing it to use that version of the API.
         api_id = : This is the identifier for the API to which this deployment applies. It links the deployment to the correct API.

        '''
        development_stage = apigatewayv2.CfnStage(self, "development_stage",
                                                  stage_name="development",
                                                  deployment_id= deployment.ref,
                                                  api_id=cnf_api.ref,
                                                  )

        """
        - This accesses the underlying node of the CfnDeployment construct. In AWS CDK, 
        each construct is represented as a node in a tree structure that manages dependencies and ordering.
        - This method establishes a dependency relationship between constructs. By adding dependencies, 
        you inform the CDK that certain resources must be created before others.
        """
        ##add the dependencies
        deployment.node.add_dependency(connect_route)
        deployment.node.add_dependency(message_route)
        deployment.node.add_dependency(disconnect_route)


        """
        SENDS AND RECIEVE MESSAGES
         construct is used to define an output value for your CloudFormation stack.
         export_name -  This is the name used for exporting the output value.
         value - constructs the WebsocketURL for the gw
                - API, region, and the "stage of the api"
        
    
        """
        wss_endpoint = CfnOutput(self, "wss_endpoint",
                                      export_name= "wssendpoint",
                                      value= f"https://{cnf_api}.execute-api.{self.region}.amazonaws.com/development")
