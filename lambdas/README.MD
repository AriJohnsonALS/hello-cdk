## Lambda functions that connects 

# connect.py
    - stores the connection to the DynamoDB table
    - puts item into the "connectionID"

# disconnect.py
    - disconnect will delete the connection from the table


# send_message.py 
- takes alll connection IDs []
- broadcast message to all connection IDS