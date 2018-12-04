# Block IP

This Lambda function uses several AWS services to accomplish this goal
* DynamoDB to track NACL block and current NACL list for a specific ACL ID
* SNS - Sends email to confirm block - also sends relevant data (blocked IP & Country of Origin) for quick look by admin or secops
* VPC - For the NACL block

Assumptions - You will need to seed a DynamoDB table with current NACLs or create new ones to be overwritten. IPs in Table won't be blocked retroactively. Just needs data to overwrite. Default max for NACLs is 20 unless you have requested an increase - then the max is 40. Just insure you use numbers less than 100 ( < 99) since the ID: 100 is typically the 'allowed' ID for all traffic inbound. If you go higher than that ID, it won't block since NACLs are evaluated in order.

#### What does it do EXACTLY?

1. Receives alert from GuardDuty via Cloudwatch
2. Cloudwatch triggers Lambda Function (this one)
3. Scans DynamoDB for oldest NACL (goal here is to overwrite blocked IPs every so often as rogue IPs change and some become legitimate again over time)
4. Overwrites oldest NACL based on epoch time
5. Writes data to DynamoDB
6. Sends SNS message to the subscription provided alerting Sysops/Secops that an IP was blocked.

I have a few extra print lines for Cloudwatch logging to read if something bombs. Then I know where the error possibly occurred if a failure happens.
