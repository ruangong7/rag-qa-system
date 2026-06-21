# PostgreSQL

## Architectural Position

PostgreSQL is the primary relational datastore for transactional platform data and structured configuration.

## Design Note

Workloads requiring vector similarity or high-scale full-text experimentation should be evaluated separately from core transactional tables.

## Governance Requirements


- Use schema migrations for all structural changes.
- Enforce backup, restore, and replication standards.
- Monitor query performance and connection pool saturation.

## Recommended Usage

- User and permission records
- Workflow state
- Audit metadata
- Operational configuration
