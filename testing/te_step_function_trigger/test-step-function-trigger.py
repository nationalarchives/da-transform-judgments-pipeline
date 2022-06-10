#!/usr/bin/env python3
import tdr_message
import sys
import json

if len(sys.argv) != 2:
    raise ValueError('usage: event')

event=sys.argv[1]
records = """{
            "Records": [{
              "messageId": "d27c13ff-4657-4768-a4d4-469dc3f809b0",
              "receiptHandle": "AQEB/cRrjaRl3wuJH1V0CF2es7bVti/t8sVWnVnD0KHL9lLZ3QodImipMWtMC9WyZ24AnD6BDPxF+z0hascDiasIkK3PDroP6/tsRG17wxTwcK6lod03ZwBBdKa/pNcCbojs2giFlWfOZK3yKYeP5dMjZM+5tM4sUMGUf8oiO2AebPQKjTihpUzMDmJPdJZ8ySULHRFEEVBH0VYbZXJexvJjN6i2fcp7T13Z78PEawLelXo7wPoGqul61r7LigQGp1OKvQqkXfx1jMeF4YY9yXoHCa7cs8lTv9rL8SBxMu9sD3ERyzGIgYG9xlMejTU/ZDQmJh53u2HQIdz7x85IyAJEEyjgFbDkZxTqUCfYWCTLiJBIXsN02co3HGCAu67P11u8zyosPtjKyUb8o6OhyDOZAA==",
              "body": \"""" + event.replace("\"", "\\\"").replace("\n","") + """\",
              "attributes": {
                "ApproximateReceiveCount": "1",
                "SentTimestamp": "1652940763028",
                "SenderId": "AROA43D4MEEVR3ZEFSQEI:botocore-session-1652940761",
                "ApproximateFirstReceiveTimestamp": "1652940763031"
              },
              "messageAttributes": {},
              "md5OfBody": "63244f156f4723c018a63f80c6bdaf05",
              "eventSource": "aws:sqs",
              "eventSourceARN": "arn:aws:sqs:eu-west-2:882876621099:dev-tre-tdr-in",
              "awsRegion": "eu-west-2"
            }]
          }"""
context = None

output = tdr_message.lambda_handler(json.loads(records), context)
print(f'tdr_message output:\n{json.dumps(output, indent=4)}')

