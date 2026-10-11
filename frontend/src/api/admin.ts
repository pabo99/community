// Typed client for the admin Program/Edition API (M1-10 redesign).
//
// Hand-written to mirror the backend Pydantic schemas; no codegen introduced.
// All calls go through the shared fetch wrapper (credentials + CSRF).

import { apiDelete, apiGet, apiPatch, apiPost } from "@/api/client";

export type ProgramIcon =
  | "github"
  | "briefcase"
  | "building"
  | "heart"
  | "users"
  | "star"
  | "code"
  | "graduation-cap"
  | "globe"
  | "sun"
  | "bolt"
  | "folder";

export const PROGRAM_ICONS: ProgramIcon[] = [
  "github",
  "briefcase",
  "building",
  "heart",
  "users",
  "star",
  "code",
  "graduation-cap",
  "globe",
  "sun",
  "bolt",
  "folder",
];

export type EditionPeriod = "annual" | "first_semester" | "second_semester";
export const EDITION_PERIODS: { label: string; value: EditionPeriod }[] = [
  { label: "Annual", value: "annual" },
  { label: "First semester", value: "first_semester" },
  { label: "Second semester", value: "second_semester" },
];

export type EditionStatus = "upcoming" | "active" | "finished";
export type EditionSource = "community" | "omegaup";

export interface Program {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  icon: ProgramIcon;
  is_standard: boolean;
  created_at: string;
  updated_at: string;
}

export interface ActiveEditionSummary {
  id: string;
  slug: string;
  name: string;
}

export interface ProgramListItem extends Program {
  edition_count: number;
  active_editions: ActiveEditionSummary[];
}

export interface Edition {
  id: string;
  program_id: string;
  slug: string;
  name: string;
  period: EditionPeriod;
  status: EditionStatus;
  starts_on: string;
  ends_on: string;
  source: EditionSource;
  external_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProgramCreate {
  name: string;
  description?: string | null;
  icon: ProgramIcon;
}

export interface ProgramUpdate {
  name?: string;
  description?: string | null;
  icon?: ProgramIcon;
}

export interface EditionCreate {
  year: number;
  period: EditionPeriod;
  name?: string | null;
  starts_on?: string | null;
  ends_on?: string | null;
}

// Only mutable fields (name, dates). slug/source/status are immutable/computed.
export interface EditionUpdate {
  name?: string;
  starts_on?: string;
  ends_on?: string;
}

export function listPrograms(): Promise<ProgramListItem[]> {
  return apiGet<ProgramListItem[]>("/api/admin/programs");
}

export function createProgram(payload: ProgramCreate): Promise<Program> {
  return apiPost<Program>("/api/admin/programs", payload);
}

export function getProgram(programId: string): Promise<Program> {
  return apiGet<Program>(`/api/admin/programs/${programId}`);
}

export function updateProgram(programId: string, payload: ProgramUpdate): Promise<Program> {
  return apiPatch<Program>(`/api/admin/programs/${programId}`, payload);
}

export function listEditions(programId: string): Promise<Edition[]> {
  return apiGet<Edition[]>(`/api/admin/programs/${programId}/editions`);
}

export function createEdition(programId: string, payload: EditionCreate): Promise<Edition> {
  return apiPost<Edition>(`/api/admin/programs/${programId}/editions`, payload);
}

export function getEdition(editionId: string): Promise<Edition> {
  return apiGet<Edition>(`/api/admin/editions/${editionId}`);
}

export function updateEdition(editionId: string, payload: EditionUpdate): Promise<Edition> {
  return apiPatch<Edition>(`/api/admin/editions/${editionId}`, payload);
}

export function deleteProgram(programId: string): Promise<void> {
  return apiDelete(`/api/admin/programs/${programId}`);
}

export function deleteEdition(editionId: string): Promise<void> {
  return apiDelete(`/api/admin/editions/${editionId}`);
}
