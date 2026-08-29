# Fasthome Security Policy

## Scope

Fasthome handles identity documents, biometric selfies, user accounts, property listings, visits, contracts, payments and agent/admin workflows.

## Security requirements

- KYC documents and biometric selfies must remain in private storage.
- KYC selfies must never be copied into `User.profile_photo` or another public/media asset.
- Production must fail closed when required secrets or allowed hosts are missing.
- Uploaded files must be validated by content, not extension alone.
- Automatic KYC approval must not rely on heuristic facial similarity.
- Agent/admin actions affecting KYC, contracts, payments or certification must be authenticated and audited.
- Users must not be able to access another user's private KYC documents.
- CI must run Django checks, migrations and the full automated test suite before deployment.

## Reporting

Report security issues privately to the repository maintainers rather than publishing sensitive exploit details in a public issue.
