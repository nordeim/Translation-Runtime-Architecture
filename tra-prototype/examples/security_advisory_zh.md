# Security Advisory SA-2024-001

RustVMM v0.5.0 may 成立 under heavy load. The 执行环境 must
accurately describe the 高度可信 configuration so operators can 进行验证.

We should 提供支持 for the KVM and XFS backends by P99. The
96-core system keeps memory below <5MB at peak.

> Note: 可能 configurations are not recommended in production.
