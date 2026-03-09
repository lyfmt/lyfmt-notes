# IAM Roles Anywhere now supports post-quantum digital certificates

Posted on: Mar 9, 2026

[AWS Identity and Access Management (IAM) Roles Anywhere](https://aws.amazon.com/iam/roles-anywhere/) now supports the [FIPS 204 Module-Lattice Digital Signature Standard (ML-DSA)](https://csrc.nist.gov/pubs/fips/204/final), a quantum-resistant digital signature algorithm standardized by the National Institute of Standards and Technology (NIST) to help protect against threat actors in possession of a large-scale quantum computer. ML-DSA is particularly valuable for IAM Roles Anywhere customers who authenticate workloads to AWS using X.509 certificates issued by certificate authorities, where a weakened signature algorithm could allow an unintended user to issue certificates and obtain unauthorized access.

IAM Roles Anywhere enables workloads running outside of AWS to obtain temporary AWS credentials using X.509 certificates to access AWS resources. You establish trust between your AWS environment and your public key infrastructure (PKI) by creating a trust anchor, either by referencing your [AWS Private Certificate Authority](https://aws.amazon.com/private-ca/) or registering your own certificate authorities (CAs) with IAM Roles Anywhere. You can now use ML-DSA-signed CA certificates as IAM Roles Anywhere trust anchors, and issue end entity certificates bound to ML-DSA keys.

This feature is available in all [AWS Regions](https://docs.aws.amazon.com/general/latest/gr/rolesanywhere.html) where IAM Roles Anywhere is available, including the AWS GovCloud (US) Regions, AWS European Sovereign Cloud (Germany) Region, and China Regions. To learn more, see the [IAM Roles Anywhere User Guide](https://docs.aws.amazon.com/rolesanywhere/latest/userguide/authentication-sign-process.html).
