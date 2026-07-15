# ADR-0001: Storage Backend = local Docker Volume

## Status
Accepted (v0.1.0)

## Context
Migration of large files (mail attachments, OneDrive GB-class items)
needs a staging area where:
- Files survive between HTTP request and worker processing
- Multiple worker replicas can share access
- We can resume a multipart upload after a process crash

Options:
1. **Named Docker volume** (single-host Coolify)
2. **S3-compatible object store** (SeaweedFS / MinIO)
3. **NFS mount** (single-host Coolify + reachable from many workers)

## Decision
**Named Docker volume mounted on all workers.**

## Rationale
- Coolify on KPX infrastructure runs single-host (deployed per KPX customer)
- All worker replicas are on the same host → share the same volume path
- No extra container to operate, no bucket to backup, no networking overhead
- Drop-in S3 replacement later via the `StorageBackend` interface

## Consequences
- Staging cannot scale across multiple Coolify nodes
- Single-host disk pressure → 3 TB staging for 100-user tenant
- When KPX moves to multi-host Coolify, only 1 service needs changing

## Follow-ups
- Implement `S3Backend` (skeleton present in `app/services/storage/s3.py`)
- Document scaling beyond single-host in OPERATOR.md
