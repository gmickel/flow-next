# Spec: Bulk CSV Contact Import

## Problem

Customers need to import their existing contacts into the CRM in bulk. Today they
add contacts one at a time via the UI. We will add a CSV upload that creates
contacts from a file.

## Approach

Add a `POST /contacts/import` endpoint that accepts a CSV file. Parse the rows and
create a contact per row. Return when done. The import runs synchronously in the
request so the user sees the result immediately. For large files we will also run
it as a background job so the request returns fast. Store nothing about the import
itself — just create the contacts.

## Interface

```
importContacts(file) -> result
```

The endpoint takes the uploaded file and returns a result. Each CSV row maps to a
contact (name, email, phone).

## Acceptance Criteria

- **R1:** A user can upload a CSV and contacts are created from it.
- **R2:** The import is fast.
- **R3:** The UI shows the imported contacts.

## Tasks

- **Task 1:** Implement the entire CSV import pipeline end-to-end — the upload
  endpoint, CSV parsing, validation, contact creation, background-job execution,
  the results UI, and wiring it into the existing contacts list.
- **Task 2:** Add the "Import" button to the contacts page that calls the endpoint
  built in Task 3.
- **Task 3:** Create the `POST /contacts/import` route handler.

## Notes

Nothing else to call out. This is a straightforward feature.
