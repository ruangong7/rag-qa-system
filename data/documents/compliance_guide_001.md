# Data Retention

## Audit Review Points


- Verify that OneTrust contains a complete and current list of customer contracts.
- Confirm that retention settings meet the 7-year requirement.
- Sample security logs from the prior year to confirm availability and retention.

## Control Objective

This control ensures that customer contract data is retained for the required period to satisfy compliance and audit obligations.

## Evidence Package

The following evidence may be used to demonstrate control effectiveness:
- Copies of customer contracts and storage location records
- Backup and recovery test reports for security logs
- Screenshots from OneTrust and the DPO Register showing retention and expiration settings

## Fact Anchors

- primary_fact: customer contracts
- required_value: 7 years
- evidence: security logs retained 1 year
- owner: DPO
- systems: OneTrust, DPO Register

## Mandatory Requirements

- Customer contracts must be retained for at least 7 years.
- Security logs related to those contracts must be retained for 1 year.

## Non-Compliance Handling

If contracts are not retained for the required duration, or if related security logs are missing, notify the DPO immediately and initiate an internal investigation.

## Out of Scope

This control does not apply to employee benefits records or API implementation data handling.

## Trigger Conditions

This guidance applies when a business team registers a new retention case in OneTrust or when an internal or external audit requires validation of contract retention controls.
