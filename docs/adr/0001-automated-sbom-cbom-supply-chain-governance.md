# ADR-0001: Automated SBOM and CBOM Supply Chain Governance Pipeline

## Metadata

| Field | Value |
|---|---|
| ADR ID | ADR-0001 |
| Status | Accepted |
| Created Date | 2026-10-11 |
| Decision Date | 2026-10-11 |
| Effective Date | 2026-10-11 |
| Architecture Domain | Security / Supply Chain Governance / Workload Identity |
| Scope | SPIRE Server & Agent Automation, Workload Identity PKI, CI/CD Pipeline |
| Decision Owner | Lead DevSecOps Architect |
| Named Decision Maker | DevSecOps Engineering & Security Architecture Team |
| Approval Authority | Architecture Review Board (ARB) / Security Governance Committee |
| Approval Evidence ID | ARB-2026-10-SEC-001 |
| APM Code(s) | SEC-SUPPLYCHAIN-01 |
| NIRA Reference(s) | NIRA-SEC-2026-042 |
| Tags | sbom, cbom, cyclonedx, spdx, supply-chain, pqc, spire, spiffe, pki, ast-analysis, devsecops |

---

## Business and Architecture Context

### Problem Statement

Modern software supply chains and zero-trust workload identity systems face rigorous regulatory and security mandates requiring machine-readable visibility into components, software dependencies, and cryptographic implementations. Executive Order 14028, NIST SP 800-218 (Secure Software Development Framework - SSDF), and NIST IR 8547 (Transition to Post-Quantum Cryptography) mandate continuous, auditable inventorying of third-party software dependencies via Software Bills of Materials (SBOMs) and cryptographic assets via Cryptographic Bills of Materials (CBOMs).

In SPIFFE/SPIRE infrastructure deployments, the SPIRE Server and SPIRE Agent act as the trust anchor and workload identity issuance engine. They manage X.509 SVIDs, JWT SVIDs, bootstrap trust bundles, mTLS communication, and node attestation keys. Without automated, continuous SBOM and CBOM generation coupled with call-site source code inspection:
1. Vulnerabilities in container base images, Python automation dependencies, or database drivers remain invisible.
2. Cryptographic algorithms used for token generation, hashing, and TLS handshakes cannot be cataloged or audited continuously against post-quantum readiness baselines.
3. Cryptographic primitives risk silent deprecation without early warning in CI/CD.

### Current Situation

Prior to this decision, the `spire-server` repository automated SPIRE High Availability clustering, PostgreSQL persistence, NGINX load balancing, and agent registration through Python scripts (`setup_demo_v9.py`, `add_agent-v5.py`) and Docker Compose configurations (`spire_setup/`). However:
1. No automated CI pipeline existed to continuously generate, validate, and publish SBOMs or CBOMs upon code commits or tag releases.
2. Cryptographic assets, certificates, and cipher suites across SPIRE configurations and Python automation were not systematically tracked in machine-readable formats.
3. Source code AST call-sites for cryptographic primitives were not evaluated during build or release.
4. CI lacked an automated validation test harness to reject schema-invalid or empty BOM artifacts.
5. No automated PQC readiness assessment was published into project governance documentation.

### Decision Drivers

- **Zero-Trust & Workload Identity Cryptographic Hygiene:** Continuous visibility into cryptographic algorithms, key lengths, and certificate trust anchors underpinning SPIRE SVID issuance and mTLS.
- **Post-Quantum Cryptography (PQC) Readiness:** Early identification of quantum-vulnerable public key algorithms (e.g., RSA, ECDSA, ECDH) and migration tracking toward NIST PQC standards (FIPS 203 ML-KEM, FIPS 204 ML-DSA, FIPS 205 SLH-DSA).
- **Regulatory & Compliance Alignment:** Adherence to EO 14028, NTIA minimum SBOM requirements, NIST SSDF, and industry-standard CycloneDX and SPDX specifications.
- **Continuous Gatekeeping in CI:** Automated validation harness enforcing valid JSON syntax, CycloneDX schema conformance, and non-empty inventory thresholds.
- **Dual-Engine Standard Interoperability:** Support for both SPDX (v2.3) and CycloneDX (v1.5/v1.6) formats to facilitate integration with diverse enterprise vulnerability scanners and policy engines.
- **Local Developer Ergonomics:** CLI scripts providing local reproduction of all CI generation, verification, and analysis workflows.

---

## Assumptions

- The repository environment contains Python 3.11+ scripts, Docker Compose definitions, and SPIRE configuration files.
- CI workflows execute on GitHub Actions runners with support for Node 24 runtime standards.
- Cryptographic transitions to Post-Quantum standards will occur over a phased multi-year window, requiring continuous visibility into both container dependencies and source code call sites.

---

## Constraints

- GitHub Actions execution limits: CI workflows must run within standard runner resource constraints without adding prohibitive build latency (< 2-3 minutes).
- Zero external vendor lock-in: Tooling must execute locally via open-source bash and Python scripts without requiring external paid SaaS services.
- Action pinning: All workflow actions must adhere to security immutability standards with SHA-pinned actions running on Node 24 runtimes.

---

## Alternatives Considered

| Option | Advantages | Disadvantages / Risks | Disposition |
|---|---|---|---|
| **Option 1: Status Quo (Ad-hoc Manual Audits)** | No CI overhead; zero configuration changes. | High operational risk; bills of materials quickly drift; no automated regression blocking; zero compliance auditability. | **Rejected** |
| **Option 2: Single-Tool SBOM Generation (Syft Only)** | Simple workflow; fast generation of CycloneDX and SPDX SBOMs. | Fails to detect cryptographic assets, certificates, or protocol configurations; no CBOM generation; no PQC readiness assessment. | **Rejected** |
| **Option 3: cbomkit-only Generation** | Generates cryptographic bill of materials in CycloneDX format. | Omits SPDX SBOM generation required by enterprise procurement; lacks semantic AST call-site correlation. | **Rejected** |
| **Option 4: Integrated Dual-Engine SBOM/CBOM + AST Analysis + Automated CI Harness (Selected)** | Comprehensive dual-engine coverage (Anchore/Syft CycloneDX & SPDX + cbomkit CBOM); deep AST semantic cryptographic call-site discovery (`scan_crypto_ast.py`); automated schema and gate verification (`test_boms.sh`); automatic PQC readiness dashboard generation (`analyze_cbom.py`); fully mirrored local execution scripts. | Slight increase in CI runtime (~60-90s); requires Python runtime setup in CI runner; generates artifacts that must be retained and versioned. | **Selected** |

---

## Decision

### Selected Option

Adopt **Option 4: Integrated Dual-Engine SBOM/CBOM + AST Analysis + Automated CI Harness** across the repository.

Specifically:
1. **GitHub Actions Workflow (`.github/workflows/sbom-cbom.yml`):**
   - Configured with Node 24 pinned actions (`actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1`, `anchore/sbom-action@006b7ce8314066bdf1765b4500370d40fa6917a3`, `cbomkit/cbomkit-action@34a3d960625ae7f7f1b59455eff93a96df090eb7`, `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065`, `actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02`).
   - Generates both CycloneDX JSON (`oss/sbom.cyclonedx.json`) and SPDX JSON (`oss/sbom.spdx.json`) SBOMs via Anchore / Syft.
   - Generates CycloneDX CBOM (`oss/cbom.json`) via `cbomkit`.
   - Executes dual-engine semantic AST cryptographic analysis via `scripts/scan_crypto_ast.py`.
   - Executes validation and test harness via `scripts/test_boms.sh`.
   - Assesses Post-Quantum Cryptography (PQC) readiness and outputs dashboard summaries via `scripts/analyze_cbom.py`.
   - Automatically maintains `docs/security/CRYPTOGRAPHIC_AUDIT.md` and archives BOM artifacts with a 90-day retention policy.
2. **Local Tooling Suite (`scripts/`):**
   - `scripts/generate_boms.sh`: Portable CLI script for local generation across source trees or Docker images.
   - `scripts/test_boms.sh`: Strict verification harness testing syntax, CycloneDX schema conformance, and component counts.
   - `scripts/scan_crypto_ast.py`: Python AST walker identifying cryptographic call-sites, key generation, and cipher instantiations.
   - `scripts/analyze_cbom.py`: PQC readiness analysis, algorithm categorization, and Markdown/JSON report generator.
   - `scripts/attach_oci_bom.sh` & `scripts/fetch_oci_cbom.py`: OCI artifact publishing and retrieval utilities.

### Rationale

This architecture establishes defense-in-depth supply chain visibility. By pairing dependency-level SBOM inventory with cryptographic-level CBOM asset tracking and AST call-site mapping, we bridge the gap between third-party package risk and application cryptography posture. For a workload identity infrastructure repository managing SPIRE servers, agents, and mTLS credentials, continuous cryptographic auditing is vital for cryptographic agility and quantum-safe readiness.

---

## Consequences

### Benefits

- **Continuous Compliance:** Instant audit readiness for modern SBOM/CBOM standards across both SPDX and CycloneDX specifications.
- **PQC Migration Visibility:** Real-time visibility into quantum-vulnerable algorithms (RSA, ECC, Diffie-Hellman) across software packages and source code.
- **Automated Verification:** The `test_boms.sh` harness prevents empty or schema-invalid BOMs from being published or merged.
- **Dual Developer & CI Experience:** Developers can run identical verification locally prior to pushing code.

### Trade-offs and Negative Consequences

- **CI Pipeline Latency:** Adds approximately 60-90 seconds to workflow execution time.
- **Maintenance Overhead:** Periodic updates to tool action SHAs and known algorithm catalogs (`known_cbom_catalog.json`) are required as cryptographic standards evolve.
- **Artifact Storage:** Retention of BOM artifacts in GitHub Actions consumes artifact storage quota (mitigated with 90-day retention policy).

### New Constraints

- Repository CI runners must provide Python 3.11+ runtime for AST and analysis scripts.
- GitHub Actions token permissions must grant `contents: write` for automated cryptographic audit report synchronization on `main` branch pushes.

### Follow-on Decisions and Activities

- Configure pull request checks to fail if high-risk deprecated algorithms (e.g., MD5 for digital signatures, DES, RC4) are newly introduced in source call-sites.
- Establish an automated schedule for container image baseline scans (`scripts/generate_boms.sh -t docker`).
- Integrate OCI cosign / notation attestation signing for generated BOM artifacts in release workflows.

---

## Security, Privacy, and Risk Considerations

- **Integrity & Authenticity:** All workflow dependencies use immutable SHA-256 commit pins to mitigate supply chain tampering of actions.
- **Confidentiality:** Scans inspect dependencies and cryptographic declarations; no secret keys, private keys, or credentials are embedded in generated BOM artifacts.
- **Supply Chain Traceability:** BOMs link directly to commit SHAs and repository metadata.

---

## Technical Debt Assessment

- **Catalog Maintenance:** The static cryptographic catalog in `scripts/known_cbom_catalog.json` must be reviewed periodically against NIST PQC standardization updates.

---

## Review and Lifecycle

- **Review Schedule:** Annual or upon major NIST PQC milestone release.
- **Supersedes:** None (Initial baseline governance record).
- **Superseded By:** None.
