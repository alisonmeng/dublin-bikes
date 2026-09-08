# Database CA certificate

Aiven refuses plaintext connections, so the client needs the service's CA
certificate to verify it is talking to the right database.

Download it from the Aiven console (service overview -> **CA Certificate**) and
save it here as `aiven-ca.pem`, then point `DB_SSL_CA` at `certs/aiven-ca.pem`.

The certificate is public information — it identifies the server, it does not
grant access — so it is safe to commit, and committing it is what lets the
GitHub Actions scraper verify the connection without extra secrets.
