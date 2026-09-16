PLACEHOLDER_MARKER_FOR_FULL_REPLACE
We are starting a new Backend project for a Partner App Integration Platform.

The goal of this backend is to provide a centralized platform for managing partner applications, clients, integrations, configurations, and deployments.

The backend will expose REST APIs that will be consumed by an Admin Portal and an existing mobile application.

==================================================
PROJECT GOAL
==================================================

We want to enable multiple partners to integrate their applications/services into our existing mobile application without requiring the user to move outside the host application.

The backend is responsible for:

- Partner management
- Partner application management
- Client/tenant management
- Partner-to-client integration management
- Integration configuration
- Draft configuration
- Deployment/publishing
- Deployment versioning
- Rollback
- Authentication
- Authorization
- Audit logging
- Mobile configuration APIs

The main business flow is:

Partner
   |
   +-- Partner Application
            |
            +-- Client Integration
                       |
                       +-- Client


Administrator configures the desired integrations.

The configuration starts as DRAFT.

When the administrator selects DEPLOY/PUBLISH, the backend creates a published deployment.

The mobile application reads ONLY the currently published deployment.

==================================================
TECHNOLOGY STACK
==================================================

Use ONLY:

- Python 3.12+
- FastAPI
- Pydantic v2
- FastAPI OpenAPI / Swagger

No database, ORM, migration tool, or containerization is used. Persistence is
an in-memory store scoped to the running process (data resets on restart).
Authentication uses simple mock bearer tokens generated in-memory (not real
JWT/PASETO signing, not a real password hashing library).

Do NOT introduce microservices.

Keep the implementation clean, maintainable and testable.

==================================================
FIRST STEP — INSPECT THE REPOSITORY
==================================================

Before implementing anything:

1. Inspect the repository.
2. Determine whether it is empty or contains an existing backend.
3. Identify existing Python configuration and project conventions.
4. Identify existing database configuration.
5. Identify existing Docker configuration.
6. Do not delete or overwrite existing files without understanding them.
7. Reuse existing infrastructure where appropriate.

Before implementation, provide:

- Repository analysis
- Proposed architecture
- Folder structure
- Database entities and relationships
- API structure
- Authentication approach
- Client/tenant identification approach
- Draft/deployment/publishing approach
- Assumptions
- Potential architectural issues

Then create the project foundation.

==================================================
BACKEND ARCHITECTURE
==================================================

Use a modular monolith.

Recommended modules:

- auth
- users
- partners
- partner_apps
- clients
- integrations
- deployments
- mobile
- audit

Recommended project structure:

app/
    main.py

    core/
        config.py
        security.py
        dependencies.py

    database/
        database.py
        base.py
        models/

    auth/
        router.py
        service.py
        schemas.py
        models.py

    users/
        router.py
        service.py
        schemas.py
        models.py

    partners/
        router.py
        service.py
        schemas.py
        models.py

    partner_apps/
        router.py
        service.py
        schemas.py
        models.py

    clients/
        router.py
        service.py
        schemas.py
        models.py

    integrations/
        router.py
        service.py
        schemas.py
        models.py

    deployments/
        router.py
        service.py
        schemas.py
        models.py

    mobile/
        router.py
        service.py
        schemas.py

    audit/
        router.py
        service.py
        schemas.py
        models.py

    common/
        exceptions.py
        responses.py
        enums.py

alembic/
tests/

Dockerfile
docker-compose.yml
requirements.txt
.env.example
.gitignore
README.md

You may improve the structure if there is a strong reason, but keep the modules clearly separated.

Route handlers should remain thin.

Business logic should be implemented in services.

==================================================
DATABASE
==================================================

Use:

- PostgreSQL
- SQLAlchemy 2.x
- Alembic

Required entities:

1. users
2. partners
3. partner_apps
4. clients
5. client_integrations
6. deployments
7. deployment_items
8. audit_logs

Use UUIDs for primary keys.

Use appropriate:

- Foreign keys
- Unique constraints
- Indexes
- Timestamps
- Referential integrity
- Appropriate delete/update behavior

==================================================
PARTNER
==================================================

Partner represents an external company/service provider.

Example:

ABC Travel
ABC Food
ABC Hotel
ABC Entertainment

Fields:

- id
- name
- description
- logo_url
- website_url
- status
- created_at
- updated_at

Use UUID primary key.

==================================================
PARTNER APPLICATION
==================================================

A Partner can have one or more applications/services.

For MVP, the primary integration type is WEB.

The architecture must support future integration types:

- WEB
- DEEPLINK
- NATIVE
- SDK
- API
- HYBRID

Fields:

- id
- partner_id
- name
- description
- integration_type
- version
- launch_url
- deep_link
- configuration
- status
- created_at
- updated_at

For WEB integrations:

launch_url is required.

Do not implement native SDK/deep-link functionality now.

Only make the data model extensible.

==================================================
CLIENT
==================================================

Client represents a customer/tenant using the platform.

Fields:

- id
- name
- code
- description
- status
- created_at
- updated_at

Client code must be unique.

Example:

Client A
Client B
Client C

==================================================
CLIENT INTEGRATION
==================================================

Client Integration represents:

"Partner Application X is enabled/configured for Client Y."

Fields:

- id
- client_id
- partner_id
- partner_app_id
- enabled
- display_name
- display_order
- configuration
- created_at
- updated_at

Validation rules:

1. Client must exist.
2. Partner must exist.
3. Partner App must exist.
4. Partner App must belong to the specified Partner.
5. Duplicate client + partner_app combinations must not be allowed.

Do not allow:

Partner A
   |
Partner App belonging to Partner B

==================================================
JSON CONFIGURATION
==================================================

Use PostgreSQL JSONB for flexible configuration.

Example:

{
    "theme": {
        "primaryColor": "#123456"
    },
    "features": {
        "booking": true,
        "offers": true
    }
}

Do NOT put important searchable fields inside JSONB.

These must remain database columns:

- client_id
- partner_id
- partner_app_id
- status
- enabled
- integration_type
- display_order
- version

==================================================
ENUMS
==================================================

Create enums.

UserRole:

SUPER_ADMIN
ADMIN
VIEWER

UserStatus:

ACTIVE
DISABLED

PartnerStatus:

DRAFT
ACTIVE
DISABLED

PartnerAppStatus:

DRAFT
ACTIVE
DISABLED

ClientStatus:

ACTIVE
DISABLED

IntegrationType:

WEB
DEEPLINK
NATIVE
SDK
API
HYBRID

DeploymentStatus:

DRAFT
PUBLISHED
ROLLED_BACK

==================================================
AUTHENTICATION
==================================================

Implement JWT authentication.

Endpoints:

POST /api/v1/auth/login

POST /api/v1/auth/refresh

POST /api/v1/auth/logout

GET /api/v1/auth/me

Use:

- Access token
- Refresh token
- Secure password hashing

Never store plaintext passwords.

Never log:

- Passwords
- Access tokens
- Refresh tokens
- JWT secrets
- API keys
- Partner credentials

Use Argon2 or bcrypt.

==================================================
AUTHORIZATION
==================================================

Initial roles:

SUPER_ADMIN
ADMIN
VIEWER

Design authorization so it can later support:

PARTNER_ADMIN
CLIENT_ADMIN

Example permissions:

partner.read
partner.create
partner.update
partner.delete

client.read
client.create
client.update
client.delete

integration.read
integration.create
integration.update
integration.delete

deployment.read
deployment.create
deployment.publish
deployment.rollback

Authorization must be enforced by the backend.

Do not rely on the frontend.

==================================================
PARTNER APIs
==================================================

Implement:

GET    /api/v1/partners
GET    /api/v1/partners/{id}
POST   /api/v1/partners
PATCH  /api/v1/partners/{id}
DELETE /api/v1/partners/{id}

Also:

GET /api/v1/partners/{id}/apps

Support pagination.

Support searching/filtering where appropriate.

Validate all request bodies using Pydantic.

==================================================
PARTNER APP APIs
==================================================

Implement:

GET    /api/v1/partner-apps
GET    /api/v1/partner-apps/{id}
POST   /api/v1/partner-apps
PATCH  /api/v1/partner-apps/{id}
DELETE /api/v1/partner-apps/{id}

A Partner App must belong to an existing Partner.

For WEB integrations, launch_url is required.

==================================================
CLIENT APIs
==================================================

Implement:

GET    /api/v1/clients
GET    /api/v1/clients/{id}
POST   /api/v1/clients
PATCH  /api/v1/clients/{id}
DELETE /api/v1/clients/{id}

Client code must be unique.

Support pagination.

==================================================
CLIENT INTEGRATION APIs
==================================================

Implement:

GET /api/v1/clients/{clientId}/integrations

POST /api/v1/clients/{clientId}/integrations

PATCH /api/v1/clients/{clientId}/integrations/{integrationId}

DELETE /api/v1/clients/{clientId}/integrations/{integrationId}

Support:

- enabled
- display_name
- display_order
- configuration

Validate all relationships.

==================================================
DRAFT CONFIGURATION
==================================================

This is one of the most important requirements.

Changes made by an administrator must NOT immediately affect the mobile application.

The system must distinguish between:

DRAFT CONFIGURATION

and

PUBLISHED CONFIGURATION.

Flow:

Current Published Configuration
             |
             v
       Admin Changes
             |
             v
      Draft Configuration
             |
             v
          Review
             |
             v
       Deploy / Publish
             |
             v
    New Published Configuration
             |
             v
        Mobile API

Mobile must ONLY consume the published configuration.

==================================================
DEPLOYMENTS
==================================================

Create:

deployments

Fields:

- id
- client_id
- version
- status
- created_by
- created_at
- published_at

Create:

deployment_items

Fields:

- id
- deployment_id
- client_integration_id
- enabled
- display_order
- configuration

Deployment statuses:

DRAFT
PUBLISHED
ROLLED_BACK

Endpoints:

POST /api/v1/clients/{clientId}/deployments

GET /api/v1/clients/{clientId}/deployments

GET /api/v1/deployments/{deploymentId}

POST /api/v1/deployments/{deploymentId}/publish

POST /api/v1/deployments/{deploymentId}/rollback

When creating a deployment:

1. Load the current desired configuration.
2. Validate it.
3. Create a deployment snapshot.
4. Copy selected integrations.
5. Copy enabled state.
6. Copy display order.
7. Copy configuration.
8. Assign deployment version.
9. Store the user who created it.

When publishing:

1. Validate the deployment.
2. Verify the deployment belongs to the correct client.
3. Verify all integrations are valid.
4. Publish the deployment.
5. Ensure only one deployment is currently published for the client.
6. Set published_at.
7. Record audit information.
8. Use a database transaction.
9. Preserve historical deployments.

Historical deployments must remain immutable.

==================================================
DEPLOYMENT VERSIONING
==================================================

Each client must have its own deployment versions.

Example:

Client A:

Deployment 1
Deployment 2
Deployment 3

Client B:

Deployment 1
Deployment 2

Versions are scoped per client.

Do not modify historical deployment records.

==================================================
ROLLBACK
==================================================

Support rollback to a previous published deployment.

Rollback must preserve history.

Do NOT delete or overwrite the deployment being rolled back.

Example:

Deployment 1
Deployment 2
Deployment 3

Rollback Deployment 3 to Deployment 2.

The system should preserve Deployment 3 and create an appropriate new deployment/version representing the rollback operation.

Maintain audit history.

==================================================
MOBILE API
==================================================

Create a dedicated mobile module.

Primary endpoint:

GET /api/v1/mobile/integrations

This endpoint must return ONLY the currently published integrations for the current client.

Example:

{
    "success": true,
    "data": {
        "client": {
            "id": "client-id",
            "name": "Client A"
        },
        "deployment": {
            "version": 3
        },
        "integrations": [
            {
                "id": "integration-id",
                "partnerId": "partner-id",
                "partnerAppId": "app-id",
                "partnerName": "ABC Travel",
                "appName": "ABC Travel",
                "displayName": "Travel",
                "logoUrl": "https://example.com/logo.png",
                "integrationType": "WEB",
                "launchUrl": "https://travel.example.com",
                "enabled": true,
                "displayOrder": 1
            }
        ]
    }
}

Rules:

- Return only published configuration.
- Return only enabled integrations.
- Sort by display_order.
- Do not expose internal database structure.
- Do not expose sensitive configuration.

==================================================
MOBILE CLIENT IDENTIFICATION
==================================================

The mobile application needs to identify which Client/Tenant it belongs to.

Do NOT rely on an unauthenticated request such as:

GET /api/v1/mobile/integrations?clientId=123

The backend must determine client context through a secure authentication mechanism.

Do not trust arbitrary client IDs from unauthenticated requests.

Design the architecture so that:

Authenticated Mobile Request
          |
          v
Authenticated Client Context
          |
          v
Published Client Configuration

Document the selected MVP authentication/client-identification approach.

==================================================
TENANT ISOLATION
==================================================

This platform supports multiple clients/tenants.

Client A must NEVER be able to:

- Read Client B integrations
- Modify Client B integrations
- Read Client B deployments
- Publish Client B deployments
- Roll back Client B deployments
- Read Client B mobile configuration

Enforce client isolation in backend services and authorization.

Do not rely on frontend filtering.

==================================================
AUDIT LOGGING
==================================================

Create audit logs for:

- Login
- Partner creation
- Partner update
- Partner deletion
- Partner App creation
- Partner App update
- Partner App deletion
- Client creation
- Client update
- Client deletion
- Integration creation
- Integration update
- Integration enable/disable
- Deployment creation
- Deployment publication
- Deployment rollback

Audit fields:

- id
- user_id
- action
- entity_type
- entity_id
- old_value
- new_value
- created_at

Never store:

- Passwords
- Access tokens
- Refresh tokens
- Secrets

==================================================
API RESPONSE FORMAT
==================================================

Use a consistent response structure.

Success:

{
    "success": true,
    "data": {}
}

Error:

{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Human readable message"
    }
}

Use correct HTTP status codes.

Do not expose internal stack traces in production.

==================================================
ERROR CODES
==================================================

Use meaningful domain errors.

Examples:

PARTNER_NOT_FOUND
PARTNER_APP_NOT_FOUND
CLIENT_NOT_FOUND
INTEGRATION_NOT_FOUND
DEPLOYMENT_NOT_FOUND
INVALID_PARTNER_APP
INVALID_CLIENT
INVALID_INTEGRATION
DUPLICATE_INTEGRATION
DEPLOYMENT_ALREADY_PUBLISHED
DEPLOYMENT_ALREADY_ROLLED_BACK
INVALID_DEPLOYMENT
UNAUTHORIZED
FORBIDDEN

Separate business/domain errors from raw database exceptions.

==================================================
PAGINATION
==================================================

Use consistent pagination for:

- Partners
- Partner Apps
- Clients
- Deployments
- Audit logs

Example:

?page=1&pageSize=20

Response:

{
    "success": true,
    "data": {
        "items": [],
        "pagination": {
            "page": 1,
            "pageSize": 20,
            "total": 100,
            "totalPages": 5
        }
    }
}

==================================================
CONFIGURATION
==================================================

Use environment variables.

Required:

DATABASE_URL

JWT_SECRET

JWT_REFRESH_SECRET

JWT_ACCESS_EXPIRATION

JWT_REFRESH_EXPIRATION

ENVIRONMENT

PORT

CORS_ORIGINS

Create:

.env.example

Never commit real secrets.

==================================================
HEALTH CHECK
==================================================

Create:

GET /health

Response:

{
    "success": true,
    "data": {
        "status": "ok"
    }
}

If practical, create a separate database readiness check.

==================================================
DOCKER
==================================================

Create:

Dockerfile

docker-compose.yml

Docker Compose should provide local development for:

- Backend
- PostgreSQL

Use environment variables.

Document the commands in README.

==================================================
ALEMBIC
==================================================

Configure Alembic correctly.

Support:

- Create migration
- Apply migration
- Rollback migration

Create the initial migration containing the required tables.

==================================================
TESTING
==================================================

Use pytest.

Create tests for:

- Authentication
- Authorization
- Partner CRUD
- Partner App CRUD
- Client CRUD
- Integration CRUD
- Deployment creation
- Deployment publishing
- Deployment rollback
- Mobile API
- Tenant isolation

Important business rules:

1. Draft configuration is NOT visible to mobile.
2. Published configuration IS visible to mobile.
3. Disabled integrations are NOT returned by mobile.
4. Historical deployments remain unchanged.
5. Client A cannot access Client B data.
6. Client A cannot modify Client B data.
7. Invalid partner/app relationships are rejected.
8. Duplicate integrations are rejected.
9. Unauthorized users cannot publish deployments.
10. Rollback preserves deployment history.

==================================================
SWAGGER / OPENAPI
==================================================

Use FastAPI OpenAPI documentation.

Organize endpoints with tags:

Authentication
Users
Partners
Partner Apps
Clients
Integrations
Deployments
Mobile
Audit

Document:

- Request parameters
- Request bodies
- Responses
- HTTP status codes
- Authentication requirements
- Error responses

==================================================
SEED DATA
==================================================

Create development seed data.

Users:

admin@example.com
viewer@example.com

Partners:

ABC Travel
ABC Food
ABC Hotel

Partner Apps:

ABC Travel Web
ABC Food Web
ABC Hotel Web

Clients:

Client A
Client B

Create sample integrations.

Create at least one published deployment.

Clearly mark seed credentials as DEVELOPMENT ONLY.

==================================================
SECURITY
==================================================

Follow secure development practices.

Do NOT:

- Hardcode passwords
- Hardcode secrets
- Log authentication tokens
- Expose password hashes
- Expose private partner credentials
- Trust arbitrary client IDs
- Expose internal stack traces
- Allow cross-client data access

Use:

- Secure password hashing
- JWT validation
- Role-based authorization
- Pydantic validation
- Environment variables
- Database transactions
- Proper HTTP status codes

==================================================
DATABASE TRANSACTIONS
==================================================

Use transactions whenever multiple records must be updated atomically.

Especially for:

- Deployment creation
- Deployment publishing
- Deployment rollback
- Deployment snapshot creation

Publishing must be atomic.

If publishing fails, the database must not be left in a partially published state.

==================================================
API VERSIONING
==================================================

All APIs must use:

/api/v1/

Examples:

/api/v1/auth/login
/api/v1/partners
/api/v1/partner-apps
/api/v1/clients
/api/v1/integrations
/api/v1/deployments
/api/v1/mobile/integrations

==================================================
FUTURE EXTENSIBILITY
==================================================

The architecture should support future features such as:

- Partner self-service
- Partner Admin
- Client Admin
- SSO
- OAuth
- Native SDK integrations
- Deep-link integrations
- API integrations
- Feature flags
- Partner-specific configuration
- Environment-specific configuration
- Approval workflows
- Scheduled deployments
- Analytics
- Integration health monitoring

Do NOT implement these now.

Only make the architecture extensible.

==================================================
DO NOT OVERENGINEER
==================================================

This is an MVP.

Do NOT introduce:

- Kubernetes
- Kafka
- Microservices
- Event sourcing
- Complex distributed systems
- Unnecessary cloud infrastructure

Keep the project simple and maintainable.

==================================================
README
==================================================

Create a complete README containing:

1. Project overview
2. Architecture
3. Technology stack
4. Folder structure
5. Database architecture
6. Entity relationships
7. Authentication
8. Authorization
9. Client/tenant isolation
10. Draft configuration
11. Deployment/publishing
12. Rollback
13. Mobile API
14. Environment variables
15. Local setup
16. PostgreSQL setup
17. Docker setup
18. Alembic migration commands
19. Seed commands
20. Running the backend
21. Swagger/OpenAPI
22. Running tests
23. API overview

==================================================
API CONTRACT
==================================================

The backend APIs must be designed so another developer can independently build the Admin Portal and another developer can integrate the existing mobile application.

Portal-facing APIs:

POST   /api/v1/auth/login

GET    /api/v1/partners
GET    /api/v1/partners/{id}
POST   /api/v1/partners
PATCH  /api/v1/partners/{id}

GET    /api/v1/partner-apps
POST   /api/v1/partner-apps
PATCH  /api/v1/partner-apps/{id}

GET    /api/v1/clients
GET    /api/v1/clients/{id}

GET    /api/v1/clients/{clientId}/integrations
POST   /api/v1/clients/{clientId}/integrations
PATCH  /api/v1/clients/{clientId}/integrations/{integrationId}

POST   /api/v1/clients/{clientId}/deployments
GET    /api/v1/clients/{clientId}/deployments

GET    /api/v1/deployments/{deploymentId}

POST   /api/v1/deployments/{deploymentId}/publish
POST   /api/v1/deployments/{deploymentId}/rollback

Mobile-facing API:

GET /api/v1/mobile/integrations

Keep the API contract stable.

Do not expose database models directly as API responses.

Use dedicated Pydantic request/response schemas.

==================================================
MOBILE RESPONSE
==================================================

The mobile API should return a stable frontend-friendly structure.

Example:

{
    "success": true,
    "data": {
        "client": {
            "id": "client-001",
            "name": "Client A"
        },
        "deployment": {
            "version": 3
        },
        "integrations": [
            {
                "id": "integration-001",
                "partnerId": "partner-001",
                "partnerAppId": "app-001",
                "partnerName": "ABC Travel",
                "appName": "ABC Travel",
                "displayName": "Travel",
                "logoUrl": "https://example.com/travel.png",
                "integrationType": "WEB",
                "launchUrl": "https://travel.example.com",
                "enabled": true,
                "displayOrder": 1
            }
        ]
    }
}

The mobile application should not need to know the database structure.

==================================================
IMPLEMENTATION PHASES
==================================================

Implement in the following phases.

PHASE 1 — PROJECT FOUNDATION

Implement:

- FastAPI application
- Project structure
- Configuration
- Database connection
- SQLAlchemy
- PostgreSQL integration
- Alembic
- Base models
- Initial models
- Initial migration
- Health endpoint
- Docker
- pytest foundation
- Swagger/OpenAPI
- README
- .env.example

PHASE 2 — AUTHENTICATION

Implement:

- Users
- Login
- JWT access token
- Refresh token
- Logout
- Authentication dependencies
- Roles
- Authorization

PHASE 3 — CORE MANAGEMENT

Implement:

- Partner CRUD
- Partner App CRUD
- Client CRUD
- Client Integration CRUD
- Validation
- Pagination
- Error handling

PHASE 4 — DEPLOYMENT

Implement:

- Draft configuration
- Deployment creation
- Deployment snapshots
- Publishing
- Deployment history
- Rollback
- Audit logging

PHASE 5 — MOBILE API

Implement:

GET /api/v1/mobile/integrations

Return only the current published configuration for the authenticated/current client.

PHASE 6 — TESTING

Implement complete tests for:

- Authentication
- Authorization
- CRUD
- Deployment
- Publishing
- Rollback
- Mobile configuration
- Tenant isolation

==================================================
IMPORTANT IMPLEMENTATION RULE
==================================================

Do not blindly implement everything in one step.

First:

1. Inspect the repository.
2. Propose the architecture.
3. Explain the database relationships.
4. Explain the API structure.
5. Explain authentication.
6. Explain client/tenant identification.
7. Explain draft → deployment → published flow.
8. Identify assumptions.
9. Create the project foundation.

After the foundation is complete, provide:

- Files created
- Files modified
- Architecture summary
- Database summary
- API summary
- Commands to run
- Migration commands
- Seed commands
- Docker commands
- Test commands
- Swagger URL
- Remaining implementation phases

Do not change the core architecture or API contract without clearly explaining why.

The backend should be implemented as a clean, modular, secure and extensible Partner App Integration Platform.