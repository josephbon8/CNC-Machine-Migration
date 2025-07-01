import json
import os
import boto3
import uuid
from datetime import datetime
from decimal import Decimal

ASSET_MAPPING = {
    "CNC-001": "47387e30-165e-4f67-b233-8ef65e2ed95f",
    "CNC-002": "11abb5c7-bb09-47a4-9054-b3e54ec2e3a1",
    "CNC-003": "3922de3f-b20c-48cc-97d2-2523d8eff8c8",
    "CNC-004": "0ecf5c17-2312-4b72-a192-17e9958f9a4b",
    "CNC-005": "3583838a-8f25-4f3c-b42e-ed7b544ea082",
}

PROPERTY_IDS = {
    "rpm": "aad0bd6d-2475-4ef0-a3ef-fe92aecd9905",
    "temperature_c": "5f51db45-6dd9-4c8d-9b22-f728d5bfdd5f",
    "vibration_mm_s": "28d8eef2-b867-4d32-b2b6-6bb1bb72fa1d",
    "operation" : "c60b8f20-502f-48fb-995c-84ba33edd0c4",
    "part_number": "7b8ad6cc-532d-421c-8f09-16a52c33da30",
    "status": "6e2ea464-8a31-425f-85db-b668005ecfc6"
}
def handler(event, context):
    print("Received event:", json.dumps(event))
    

    # Extract payload safely
    payload = event.get("message", event)

    required_keys = [
        "machine_id", "timestamp", "rpm", "temperature_c",
        "vibration_mm_s", "operation", "part_number", "status"
    ]

    # Check for missing keys
    missing_keys = [k for k in required_keys if k not in payload]
    if missing_keys:
        print(f"Missing keys in payload: {missing_keys}")
        return {
            "statusCode": 400,
            "body": f"Missing keys: {missing_keys}"
        }
    item = {
        "machine_id": payload["machine_id"],
        "timestamp": payload["timestamp"],
        "rpm": Decimal(str(payload["rpm"])),
        "temperature_c": Decimal(str(payload["temperature_c"])),
        "vibration_mm_s": Decimal(str(payload["vibration_mm_s"])),
        "operation": payload["operation"],
        "part_number": payload["part_number"],
        "status": payload["status"]
    }


    try:
        print("Payload received for DynamoDB:")
        print(json.dumps(payload, indent=2))
        table_name = os.environ["DYNAMODB_CNC_TABLE"]
        print(table_name)

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        print("Attempting to write to DynamoDB table:", table_name)
        response = table.put_item(Item=item)
        print("DynamoDB put_item response:", response)
        # Store in DynamoDB
        table.put_item(Item=item)

        # Send to SiteWise
        entries = []
        
        timestamp = int(datetime.fromisoformat(
            payload["timestamp"].replace("Z", "+00:00")).timestamp())
        property_types = {
            "operation": "string",
            "part_number": "string",
            "status": "string",
            "rpm": "integer",                
            "temperature_c": "double",
            "vibration_mm_s": "double"
        }
        asset_id = ASSET_MAPPING[payload["machine_id"]]
        for key, prop_id in PROPERTY_IDS.items():
            value_type = property_types[key]
    
            if value_type == "string":
                value_payload = {"stringValue": str(payload[key])}
            elif value_type == "double":
                value_payload = {"doubleValue": float(payload[key])}
            elif value_type == "integer":
                value_payload = {"integerValue": int(payload[key])}
            else:
                raise ValueError(f"Unsupported type for property: {key}")
            #if key in STRING_PROPERTIES:
             #   value_payload = {"stringValue": str(payload[key])}
            #else:
                #value_payload = {"doubleValue": float(payload[key])}

            entry = {
                "entryId": str(uuid.uuid4()),
                "assetId": asset_id,
                "propertyId": prop_id,
                "propertyValues": [
                    {
                        "value": value_payload,
                        "timestamp": {
                            "timeInSeconds": timestamp,
                            "offsetInNanos": 0
                            },
                    "quality": "GOOD"
                    }
                ]
            }

            entries.append(entry)
       
        sitewise = boto3.client("iotsitewise")
        response = sitewise.batch_put_asset_property_value(entries=entries)
        print("SiteWise response:", response)
        
       

       

        return {"statusCode": 200, "body": "Success"}

    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "body": str(e)}
