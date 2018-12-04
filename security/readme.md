# Block IP

This Lambda function uses several AWS services to accomplish this goal
* Dynamo to track NACL block and current NACL list for a specific ACL ID
* SNS - Sends email to confirm block - also sends relevant data (blocked IP & Country of Origin) for quick look by admin or secops
* VPC - For the NACL block
