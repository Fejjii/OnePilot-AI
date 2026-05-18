# NovaEdge Solutions — Data Privacy Policy

This document is the customer-facing summary of how NovaEdge handles personal and
business data. The legal text lives in the master services agreement and the data
processing addendum.

## Scope
This policy applies to all data NovaEdge processes on behalf of a customer in connection
with our AI automation services. It covers:

- Email content and metadata.
- CRM records (contacts, deals, tickets).
- Knowledge-base documents the customer uploads.
- Calendar events.
- Conversation transcripts and AI responses.
- Usage logs and audit logs.

It does **not** cover NovaEdge marketing data; that is governed by our public privacy notice
at `novaedge.io/privacy`.

## Roles
- **Customer:** Data Controller for the personal data they upload or process via NovaEdge.
- **NovaEdge:** Data Processor under GDPR / PIPEDA. We process only on documented
  instructions from the Customer.

## What We Collect and Why
| Category                 | Purpose                                              | Retention                    |
|--------------------------|------------------------------------------------------|------------------------------|
| Workspace metadata       | Provide the service                                  | Lifetime of the account      |
| Uploaded documents       | Power retrieval-augmented answers                    | Until customer deletes       |
| AI prompts and responses | Audit, debugging, eval harness                       | 90 days, then anonymized     |
| Usage events             | Quota enforcement, billing                           | 24 months                    |
| Audit logs               | Tamper-evident record of AI actions                  | 24 months                    |
| Support tickets          | Customer service                                     | 36 months                    |

Customers can shorten any of these retention periods by contract.

## Where Data Is Stored
- Default region: **`ca-central-1`** (Canada).
- EU customers: **`eu-central-1`** (Frankfurt).
- US-residency customers: **`us-east-1`** (N. Virginia).

Cross-region transfers are not performed without the customer's written consent. EU customer
data is not transferred outside the EU/EEA except under standard contractual clauses.

## Third-Party Sub-processors
We use a small set of audited sub-processors:

- **OpenAI** for LLM inference and embeddings.
- **Anthropic** for fallback / specialized LLM use.
- **Qdrant Cloud** (managed) or self-hosted Qdrant for vector storage.
- **AWS / GCP** for compute and storage.
- **HubSpot, Google, Microsoft** when the customer authorizes the corresponding integration.

A current sub-processor list is maintained at `novaedge.io/subprocessors`. We notify
customers at least **30 days** in advance of any material change.

## Model Training Policy
We do **not** allow third-party model providers to train on customer data.

- OpenAI: we use API endpoints with the `data-not-used-for-training` setting.
- Anthropic: we contract with the equivalent non-training enterprise setting.
- We do not train our own foundation models on customer data either.

## Data Subject Requests
NovaEdge supports the following requests on behalf of the Customer (as Controller):

- Access — provide the data we hold about a person.
- Deletion — remove the data after Customer authorization.
- Rectification — correct inaccurate data.
- Portability — export data in JSON.
- Objection / restriction — pause processing.

We respond to requests via the Customer's account-admin email within **5 business days**.

## Security Measures
See `security_policy.md`. In summary:

- TLS 1.2+ in transit, AES-256 at rest.
- Least-privilege IAM with mandatory MFA for engineers.
- Per-tenant logical isolation (every record carries `organization_id`).
- Quarterly access reviews; annual third-party penetration test.

## Breach Notification
If a confirmed breach impacts customer data, we notify the customer's security contact within
**72 hours** of detection, including:

- The nature of the breach.
- Approximate number of records affected.
- Mitigations already taken.
- Steps the customer should take.

## Contact
Privacy questions: **`privacy@novaedge.io`**
DPO: **`dpo@novaedge.io`**
Legal: **`legal@novaedge.io`**
