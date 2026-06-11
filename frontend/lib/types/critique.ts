export interface CritiqueScore {
  score: number;
  max: number;
  note?: string;
}

export interface TopFix {
  priority: string; // "high" | "medium" | "low"
  fix: string;
}

export type CritiqueVerdict = "STRONG MATCH" | "NEEDS WORK" | "WEAK MATCH";
export type CritiqueColor = "green" | "yellow" | "red";

export interface Critique {
  total: number;
  verdict: CritiqueVerdict;
  scores: Record<string, CritiqueScore>;
  keywords_found: string[];
  keywords_missing: string[];
  top_fixes: TopFix[];
}
