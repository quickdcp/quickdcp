/**
 * QuickDCP Node SDK (fixed)
 * Minimal TypeScript client for QuickDCP API.
 *
 * Targets Node 18+ (built-in fetch). If you need Node <18, polyfill fetch.
 */

import { createHash, createHmac } from "crypto";
import * as fs from "fs";
import * as path from "path";

// -----------------------------
// Types
// -----------------------------
export type HeadersInit = Record<string, string>;

export interface ClientOptions {
  baseUrl: string; // e.g., https://api.quickdcp.com
  customer: string; // X-QD-Customer value
  apiKey: string; // Authorization: QuickDCP <apiKey>
}

export interface RenderProfile {
  res?: string;
  shape?: string;
  extras?: Record<string, unknown>;
}

export interface RenderRequest {
  job_id?: string;
  input_key?: string;
  profile?: RenderProfile;
}

export interface RenderResponse {
  job_id: string;
  status: string; // QUEUED
}

export interface JobSummary { job_id: string; status: string }

export interface ManifestQC { audio_lufs?: number; video_issues?: number; subtitle_sync_ms?: number }
export interface Manifest {
  job_id: string;
  profile?: Record<string, unknown>;
  outputs?: Record<string, unknown>;
  qc?: ManifestQC;
  proof?: Record<string, unknown>;
  kdm?: Array<Record<string, unknown>>;
}

export interface ProofInitRes { job_id: string; manifest_sha256: string; tsq_der: string }
export interface ProofAckRes { job_id: string; status: string; manifest_sha256: string; tsa_ok: boolean }

export interface UploadInitRes { upload_id: string; key: string; size: number; sha256: string }
export interface PartSignRes { url: string }
export interface CompletePart { ETag: string; PartNumber: number }
export interface HeadRes { key: string; exists: boolean; size?: number }

// -----------------------------
// Utilities
// -----------------------------
async function jsonFetch<T>(url: string, init: RequestInit): Promise<T> {
  const res = await fetch(url, init as any);
  const text = await res.text();
  let data: any = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* not json */ }
  if (!res.ok) {
    const payload = data ?? { error: text || "http_error" };
    const err = new Error(`HTTP ${res.status}: ${JSON.stringify(payload)}`);
    (err as any).status = res.status;
    (err as any).payload = payload;
    throw err;
  }
  return data as T;
}

function baseHeaders(opts: ClientOptions): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-QD-Customer": opts.customer,
    Authorization: `QuickDCP ${opts.apiKey}`,
  };
}

function sha256FileHex(filePath: string, chunk = 1024 * 1024): Promise<string> {
  return new Promise((resolve, reject) => {
    const h = createHash("sha256");
    const s = fs.createReadStream(filePath, { highWaterMark: chunk });
    s.on("data", (b) => h.update(b));
    s.on("error", reject);
    s.on("end", () => resolve(h.digest("hex")));
  });
}

function sha256Base64(buf: Buffer): string {
  return createHash("sha256").update(buf).digest("base64");
}

// -----------------------------
// Client
// -----------------------------
export class QuickDCP {
  readonly baseUrl: string;
  readonly headers: HeadersInit;

  constructor(private opts: ClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, "");
    this.headers = baseHeaders(opts);
  }

  // Jobs
  async renderJob(req: RenderRequest): Promise<RenderResponse> {
    return jsonFetch<RenderResponse>(`${this.baseUrl}/jobs/render`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(req),
    });
  }

  async getJob(jobId: string): Promise<Manifest | { job_id: string; status: string }> {
    return jsonFetch(`${this.baseUrl}/jobs/${encodeURIComponent(jobId)}`, {
      method: "GET",
      headers: { ...this.headers, "Content-Type": "" },
    });
  }

  async listJobs(): Promise<JobSummary[]> {
    return jsonFetch(`${this.baseUrl}/jobs`, {
      method: "GET",
      headers: { ...this.headers, "Content-Type": "" },
    });
  }

  // Proof
  async proofInit(jobId: string): Promise<ProofInitRes> {
    return jsonFetch(`${this.baseUrl}/proof/init`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({ job_id: jobId }),
    });
  }

  async proofAckTsa(jobId: string, tsrBase64: string, tsaCertPem?: string): Promise<ProofAckRes> {
    return jsonFetch(`${this.baseUrl}/proof/ack/tsa`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({ job_id: jobId, tsr_base64: tsrBase64, tsa_cert_pem: tsaCertPem }),
    });
  }

  async proofStatus(jobId: string): Promise<ProofAckRes> {
    return jsonFetch(`${this.baseUrl}/proof/status/${encodeURIComponent(jobId)}`, {
      method: "GET",
      headers: { ...this.headers, "Content-Type": "" },
    });
  }

  // Upload (multipart)
  async uploadInit(filename: string, size: number, sha256: string): Promise<UploadInitRes> {
    const form = new URLSearchParams();
    form.set("filename", filename);
    form.set("size", String(size));
    form.set("sha256", sha256);
    const res = await fetch(`${this.baseUrl}/upload/init`, {
      method: "POST",
      headers: { ...this.headers, "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
    if (!res.ok) throw new Error(`uploadInit failed: ${res.status}`);
    return (await res.json()) as UploadInitRes;
  }

  async signPart(key: string, uploadId: string, partNumber: number): Promise<PartSignRes> {
    const form = new URLSearchParams();
    form.set("key", key);
    form.set("upload_id", uploadId);
    form.set("part_number", String(partNumber));
    const res = await fetch(`${this.baseUrl}/upload/part`, {
      method: "POST",
      headers: { ...this.headers, "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
    if (!res.ok) throw new Error(`signPart failed: ${res.status}`);
    return (await res.json()) as PartSignRes;
  }

  async uploadComplete(key: string, uploadId: string, parts: CompletePart[]): Promise<{ ok: boolean; key: string }> {
    return jsonFetch(`${this.baseUrl}/upload/complete`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify({ key, upload_id: uploadId, parts }),
    });
  }

  async uploadHead(key: string): Promise<HeadRes> {
    const url = new URL(`${this.baseUrl}/upload/head`);
    url.searchParams.set("key", key);
    return jsonFetch(url.toString(), {
      method: "GET",
      headers: { ...this.headers, "Content-Type": "" },
    });
  }

  /**
   * High-level convenience: upload a local file via multipart and return the S3 key
   */
  async uploadFile(filePath: string, partSizeMB = 64): Promise<{ key: string; sha256: string; size: number; parts: number }> {
    const abs = path.resolve(filePath);
    const size = fs.statSync(abs).size;
    const sha = await sha256FileHex(abs);

    const init = await this.uploadInit(path.basename(abs), size, sha);
    const parts: CompletePart[] = [];

    const partSize = Math.max(5, partSizeMB) * 1024 * 1024; // S3 min 5MB
    const fd = fs.openSync(abs, "r");
    try {
      let partNo = 1;
      let offset = 0;
      const buf = Buffer.allocUnsafe(partSize);
      while (offset < size) {
        const toRead = Math.min(partSize, size - offset);
        const read = fs.readSync(fd, buf, 0, toRead, offset);
        const chunk = buf.subarray(0, read);
        const { url } = await this.signPart(init.key, init.upload_id, partNo);
        const put = await fetch(url, {
          method: "PUT",
          headers: { "x-amz-checksum-sha256": sha256Base64(chunk) },
          body: chunk,
        });
        if (!(put.status === 200 || put.status === 201)) {
          const t = await put.text();
          throw new Error(`part PUT failed: ${put.status} ${t}`);
        }
        const etag = put.headers.get("etag")?.replace(/\"/g, "");
        if (!etag) throw new Error("missing ETag on part PUT");
        parts.push({ ETag: etag, PartNumber: partNo });
        offset += read;
        partNo += 1;
      }
    } finally {
      fs.closeSync(fd);
    }

    await this.uploadComplete(init.key, init.upload_id, parts);
    return { key: init.key, sha256: sha, size, parts: parts.length };
  }
}

// Default export for CommonJS consumers via transpiled output
export default QuickDCP;
