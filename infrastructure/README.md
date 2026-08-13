# Infrastructure

Local PostgreSQL is defined in the repository-level `docker-compose.yml`.
Production infrastructure will be selected after the MVP hosting provider,
region, backup policy, object storage, and secrets manager are agreed.

Do not place production credentials or state files in this directory.
