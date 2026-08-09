# Flutter onboarding contract

The onboarding sequence is `POST /api/v1/accounts/profiles/`, `POST
/api/v1/accounts/photos/`, `PATCH /api/v1/accounts/photos/{id}/`, `POST
/api/v1/accounts/face-verify/`, then `POST /api/v1/accounts/pledges/`. Each
request is independently retryable; there is no global transaction across
endpoints.

For an authenticated non-staff user, profile, photo, and pledge ownership always
comes from the authenticated account. A repeated profile create returns a typed
validation error; after a timeout, reconcile with `GET /api/v1/accounts/profiles/me/`
and update that profile if needed. Pledge POST is idempotent and returns `201` on
first creation or `200` on retry.

Photos accept JPG, PNG, or WEBP (up to 10 MB and 4096x4096); a profile may have
at most four active photos with unique orders 1 through 4. Gallery photos require
face detection and an embedding, but not liveness. Selfie verification requires
liveness and compares only with the designated main photo.

Voice introductions accept AAC/M4A files up to 1 MB. The backend has no media
duration parser, so the 30-second limit remains a client-side validation.

No AI compatibility-test endpoint exists in this backend. Routing users to an AI
test after completed onboarding remains client-side follow-up scope.
