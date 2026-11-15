# SAMAY installable app

Production: https://samay-colossus-app.vercel.app

This PWA preserves the compiled frontend from https://samay-colossus.vercel.app and proxies /backend/* and /api/* to that site's existing backend. The original Vercel project was not accessible to the signed-in resonance19 account, so this is a separate production deployment; the original site was not changed. Backend availability/data limitations remain those of the original service.

The frontend source fingerprint is recorded in source-snapshot.json. This deployment is a snapshot, not an automatic synchronization with future original-site updates. The existing workspace frontend is a different version and was not substituted for the requested live site.

Features: standalone manifest; 192/512 icons plus a maskable icon and Apple touch icon; Android install prompt when supported; Safari Add to Home Screen instructions; offline app shell; explicit connectivity warning; safe-area support. The service worker never caches backend API responses or submitted financial inputs. Updates are content-hashed during build and activate when old app windows close.

Build: node build.mjs in this directory. Deploy from repo root: npx vercel deploy installable-app --prod --yes --project samay-colossus-app --scope resonance19.

Verification, 14 November 2026: local installation-help test, manifest/icon checks, service-worker activation, offline reload and API-cache exclusion passed. Public URLs returned correct content types. Live Chromium Page.getAppManifest returned no errors; Page.getInstallabilityErrors returned no errors; no page errors were observed; proxied health returned ok; offline reload passed with no API cache entries. Details are in verification.json. Native iPhone/Android installation was not physically exercised.

Install on Android: open the production URL in Chrome and tap Install SAMAY, or use the browser Install app menu. On iPhone: open in Safari, tap Share, then Add to Home Screen, then Add. Financial decisions still need network access and verified data.
