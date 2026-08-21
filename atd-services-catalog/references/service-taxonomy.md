# ATD Service Taxonomy

Use this controlled vocabulary for every catalog update. Extend it only when evidence does not fit an existing category; record the new definition before applying it.

## Canonical Service Naming

Name each service as a concise Title Case noun phrase:

`[Architecture area or business object] + [service type]`

Examples:

- `Enterprise Architecture Capability Assessment`
- `Business Architecture Development`
- `Data Architecture Design`
- `Application Portfolio Assessment`
- `Technology Architecture Roadmap`
- `EA Governance Framework Design`
- `EA Platform Implementation`
- `Architecture Training and Knowledge Transfer`

Apply these rules:

- Describe the reusable service, not the client, project, document, vendor, date, phase number, or team name.
- Prefer the primary outcome over internal task wording.
- Use a singular service name even when multiple instances were delivered.
- Keep product or methodology names in the scope description unless they materially distinguish the service.
- Preserve the original wording in the source reference or scope summary; do not force a mapping that changes meaning.
- Merge labels such as `review`, `health check`, and `maturity review` into `Assessment` only when their purpose and deliverables are equivalent.
- Merge labels such as `setup`, `deployment`, and `rollout` into `Implementation` only when their scope is equivalent.
- Use separate names when one item is advisory and another includes implementation or managed operation.

## Service Domains

| Service Domain | Use For | Default BDAT Domain |
|---|---|---|
| EA Strategy and Capability | EA vision, principles, capability or maturity assessment, strategy, and capability uplift | Cross-BDAT |
| Business Architecture | Business capability, value stream, operating model, organization, and business process architecture | Business |
| Data Architecture | Data domains, models, governance design, information architecture, and data roadmap | Data |
| Application Architecture | Application landscape, portfolio, rationalization, integration architecture, and application roadmap | Application |
| Technology Architecture | Infrastructure, cloud, network, workplace, middleware, and technology standards or roadmap | Technology |
| Security Architecture | Security principles, controls, patterns, target architecture, and security roadmap | Cross-BDAT |
| EA Governance | Architecture governance, review boards, policies, decision rights, compliance, and assurance | Cross-BDAT |
| EA Platform and Repository | EA tooling, metamodel, repository, configuration, migration, integration, and platform adoption | Cross-BDAT |
| Portfolio and Roadmap | Initiative portfolio, transition states, dependencies, prioritization, and transformation roadmap | Cross-BDAT |
| Standards and Reference Architecture | Reusable standards, patterns, principles, reference models, and reference architectures | Cross-BDAT |
| Transformation and Operating Model | Transformation design, target operating model, implementation planning, and organizational alignment | Cross-BDAT |
| Training and Knowledge Transfer | Workshops, coaching, enablement, playbooks, and formal knowledge transfer | Not Applicable |
| EA Advisory and Managed Services | Ongoing architecture advisory, architecture office augmentation, repository operation, or managed EA capability | Cross-BDAT |
| Other | Evidence-backed service that does not yet fit the controlled vocabulary | Not Applicable |

## BDAT Domains

Use exactly one of these values:

- `Business`
- `Data`
- `Application`
- `Technology`
- `Cross-BDAT`
- `Not Applicable`

Override a default only when the documented service's primary scope supports the change. Use `Cross-BDAT` for genuinely integrated multi-domain work, not merely because a project mentions several domains.

## Standard Service Types

Prefer these outcome-oriented endings when they fit the evidence:

| Service Type | Meaning |
|---|---|
| Assessment | Baseline, maturity, health, gap, or current-state evaluation |
| Strategy | Direction, principles, objectives, and strategic choices |
| Design | Target-state design, framework, model, blueprint, or architecture definition |
| Development | Creation of architecture content, standards, or reusable assets |
| Roadmap | Sequenced initiatives, transition states, dependencies, and priorities |
| Implementation | Configuration, deployment, rollout, migration, or operationalization |
| Governance | Decision rights, controls, review mechanisms, policies, and assurance |
| Training and Knowledge Transfer | Structured enablement, coaching, workshops, or handover |
| Advisory | Time-bound expert guidance without ownership of ongoing operation |
| Managed Service | Recurring operational responsibility against an agreed service scope |
| Support | Post-implementation assistance, troubleshooting, or stabilization |

When none fits, use a plain evidence-based noun phrase and flag the naming decision for review rather than inventing a fashionable label.

