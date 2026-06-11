"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listRoles } from "@/lib/api/roles";
import { useAccessToken } from "@/lib/store/auth";

interface Props {
  value: string;
  onChange: (value: string) => void;
}

const COMMON_ROLES = [
  { id: "software_engineer", display_name: "Software Engineer" },
  { id: "ai_engineer", display_name: "AI / ML Engineer" },
  { id: "frontend_engineer", display_name: "Frontend Engineer" },
  { id: "backend_engineer", display_name: "Backend Engineer" },
  { id: "full_stack_engineer", display_name: "Full Stack Engineer" },
  { id: "data_scientist", display_name: "Data Scientist" },
  { id: "data_engineer", display_name: "Data Engineer" },
  { id: "devops_engineer", display_name: "DevOps / Platform Engineer" },
  { id: "mobile_engineer", display_name: "Mobile Engineer (iOS/Android)" },
  { id: "security_engineer", display_name: "Security Engineer" },
  { id: "product_manager", display_name: "Product Manager" },
  { id: "other", display_name: "Other — type your own" },
];

function toRoleId(name: string): string {
  return name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

export default function RoleSelector({ value, onChange }: Props) {
  const accessToken = useAccessToken();
  const [customText, setCustomText] = useState("");

  // Fetch user's saved custom roles from backend (non-blocking — common roles always show)
  const { data: backendRoles } = useQuery({
    queryKey: ["roles", accessToken],
    queryFn: () => listRoles(accessToken!),
    enabled: !!accessToken,
    staleTime: 5 * 60 * 1000,
  });

  // Merge: common roles + any backend roles not already in the common list
  const commonIds = new Set(COMMON_ROLES.map((r) => r.id));
  const extraRoles = (backendRoles ?? []).filter((r) => !commonIds.has(r.id));

  const allRoles = [
    ...COMMON_ROLES.filter((r) => r.id !== "other"),
    ...extraRoles.map((r) => ({ id: r.id, display_name: r.display_name })),
    { id: "other", display_name: "Other — type your own" },
  ];

  const isOther = value === "other" || (value !== "" && !commonIds.has(value) && !extraRoles.find((r) => r.id === value));
  const selectValue = isOther && !extraRoles.find((r) => r.id === value) ? "other" : value;

  function handleSelect(id: string) {
    if (id === "other") {
      onChange("other");
      setCustomText("");
    } else {
      onChange(id);
    }
  }

  function handleCustomChange(text: string) {
    setCustomText(text);
    const id = toRoleId(text);
    onChange(id || "other");
  }

  return (
    <div className="space-y-2">
      <select
        value={selectValue}
        onChange={(e) => handleSelect(e.target.value)}
        className="w-full rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-accent"
      >
        <option value="" disabled>Select a role type</option>
        {allRoles.map((r) => (
          <option key={r.id} value={r.id}>
            {r.display_name}
          </option>
        ))}
      </select>

      {selectValue === "other" && (
        <input
          type="text"
          value={customText}
          onChange={(e) => handleCustomChange(e.target.value)}
          placeholder="e.g. Quantitative Researcher, Solutions Architect"
          className="w-full rounded-lg border border-line bg-paper-raised px-3 py-2 text-sm text-ink placeholder-ink-faint focus:outline-none focus:ring-2 focus:ring-accent"
        />
      )}

      {selectValue === "other" && customText.trim() && (
        <p className="text-xs text-ink-faint">
          Role ID: <span className="font-mono">{toRoleId(customText)}</span> — the AI will generate a tailoring strategy for this role.
        </p>
      )}
    </div>
  );
}
