export interface PersonalInfo {
  name: string;
  email: string;
  phone?: string;
  location?: string;
  linkedin?: string;
  github?: string;
  portfolio?: string;
}

export interface VisaStatus {
  type: string; // "citizen" | "green_card" | "h1b" | "opt" | "cpt" | "tn" | "other" | "unknown"
  needs_sponsorship: boolean;
  stem_extension_eligible: boolean;
}

export interface Bullet {
  id: string;
  text: string;
  themes: string[];
  metrics: string[];
  tech_stack: string[];
}

export interface Education {
  id: string;
  degree: string;
  school: string;
  location?: string;
  dates?: string;
  gpa?: number;
}

export interface Experience {
  id: string;
  title: string;
  company: string;
  location?: string;
  dates?: string;
  level?: string;
  bullets: Bullet[];
}

export interface Project {
  id: string;
  name: string;
  subtitle?: string;
  stack: string[];
  themes: string[];
  text: string;
  metrics: string[];
  url?: string;
}

export interface Profile {
  version: number;
  personal: PersonalInfo;
  visa_status?: VisaStatus;
  education: Education[];
  experience: Experience[];
  projects: Project[];
  skills: Record<string, string[]>;
}

export interface FlaggedField {
  path: string;
  reason: string;
}

export interface ParseFromResumeResponse {
  profile: Profile;
  extraction_confidence: Record<string, number>;
  flagged_fields: FlaggedField[];
  raw_extracted_text: string;
}
