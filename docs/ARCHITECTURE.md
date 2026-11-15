# Architecture and stage boundary

React, TypeScript, Vite and Tailwind provide the mobile shell. React Router handles six sections; TanStack Query fetches the catalog with explicit loading and failure states. React Hook Form, Zod, Recharts and Lucide are installed for subsequent workflow implementation. FastAPI owns API behavior and future financial calculations. Pydantic validates operator configuration. SQLAlchemy and Alembic manage SQLite development and PostgreSQL deployment. No forecasting libraries or models are active at this stage; add Pandas, NumPy and scikit-learn with the evaluated data pipeline. LightGBM requires comparative evaluation.

## Data structure

Crops and markets carry localized names and provenance. Varieties belong to crops; grades describe observation quality. Market observations reference crop, market, optional variety/grade and data source, store INR per quintal and observation time, and deduplicate source record IDs. Import history captures status, timestamps and evidence. Model versions retain evaluation metadata; forecasts reference model, crop, market and target time. Farmer profiles contain only authentication subject and preferred language. Selling plans allow a nullable farmer owner and store assumptions. Calculation records retain engine version and evidence. Application configuration holds extensible settings. Thirteen domain tables are created in the initial migration.

## Farmer journey design

1. Choose Kannada or English; language persists on this device.
2. Select crop and an observation-supported mandi.
3. One short form collects harvest in quintals, optional actual buyer price in INR/quintal, immediate cash need in INR, storage availability, storage cost and period, deterioration assumption, transport, handling and other sale expenses. Label all these as farmer assumptions.
4. Backend validates units, nonnegative values, quantity limits and source freshness. Block calculations when required evidence is absent. Prioritize cash need and disclose any shortfall before considering holding.
5. Show sell-now quantity, remaining quantity, costs and uncertainty, followed by a plain-language explanation. Distinguish observations, forecasts and assumptions. Holding must remain optional.
6. Edit inputs to compare recalculated plans. Save locally with explicit device privacy information or optionally sign in for history.

Only language, navigation and catalog selection are implemented now. Input collection, recommendations, comparisons and saving remain subsequent stages.

## Authentication architecture

Public health/catalog and future anonymous calculation routes require no registration. Optional account history will use an OIDC provider with server-side issuer, audience, signature and expiry validation. Map the verified subject to a minimal farmer profile; scope every history operation by that subject. Never trust a client-supplied farmer ID. Anonymous saved plans will need high-entropy capability tokens stored hashed, expiry, and explicit ownership transfer on sign-in. Do not expose plan reads until those authorization checks exist. No login or account endpoints are implemented in this stage. No phone, address, landholding or identity documents are collected.

## Reliability and evidence

Request IDs correlate structured JSON access logs and generic error responses. Avoid logging farmer inputs. Catalog failures are visible with retry; cached market prices are not used. Real observation ingestion must enforce freshness, provenance, units and validation before enabling recommendations. Kannada terminology needs native-speaker review. Offline plan saving is designed, not implemented.
