from app.models.pipeline import TailoredContent, TailoredExperience, TailoredProject
from app.models.profile import Profile
from app.utils.latex_escape import escape
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Position-based trim ladder.  Each step is cumulative — _apply_trim applies
# all adjustments up to and including the requested step.
#
# Step 0: full content — no trim
# Step 1: drop 1 bullet from oldest role
# Step 2: drop 1 more from oldest; if 0 remain, drop the entire role entry
# Step 3: truncate projects to 2
# Step 4: truncate projects to 1
# Step 5: drop 1 bullet from second-oldest role
# Step 6: drop 1 more from second-oldest
# Step 7: drop 1 bullet from newest role (last resort)
_TRIM_STEPS = 8


class LatexAssembler:
    """Builds a complete .tex string from a Profile + TailoredContent.

    The tailor agent returns fully-reworded bullet text in TailoredContent.
    This class renders it into a .tex file.  The trim ladder is applied here
    before rendering so the compiler only ever sees a single tex string.

    Section order: header → summary → education → skills → experience → projects
    """

    def assemble(
        self,
        profile: Profile,
        tailored: TailoredContent,
        trim_step: int = 0,
    ) -> str:
        """Render a .tex document.  trim_step applies the position-based trim ladder."""
        trimmed = self._apply_trim(tailored, trim_step)

        lines: list[str] = []
        lines.append(self._preamble())
        lines.append(self._personal_section(profile))
        lines.append(self._summary_section(trimmed))
        lines.append(self._education_section(profile))
        lines.append(self._skills_section(trimmed))
        lines.append(self._experience_section(profile, trimmed))
        lines.append(self._projects_section(profile, trimmed))
        lines.append(r"\end{document}")

        return "\n".join(ln for ln in lines if ln)

    def trim_steps_count(self) -> int:
        return _TRIM_STEPS

    # ── Trim ladder ────────────────────────────────────────────────────────────

    def _apply_trim(self, tailored: TailoredContent, step: int) -> TailoredContent:
        """Return a new TailoredContent with trimming applied cumulatively up to step."""
        exps = [
            TailoredExperience(role_id=e.role_id, bullets=list(e.bullets))
            for e in tailored.experience
        ]
        projs = list(tailored.projects)

        # Steps 1–2: trim oldest role (exps[-1])
        oldest_drops = min(step, 2)  # at most 2 bullets dropped from oldest
        if oldest_drops > 0 and exps:
            remaining = exps[-1].bullets[:-oldest_drops]
            if remaining:
                exps[-1] = TailoredExperience(role_id=exps[-1].role_id, bullets=remaining)
            else:
                exps = exps[:-1]  # drop entire oldest role

        # Steps 3–4: truncate projects
        if step >= 3:
            projs = projs[:2]
        if step >= 4:
            projs = projs[:1]

        # Steps 5–6: trim second-oldest role (last entry after possible drop above)
        second_oldest_drops = 0
        if step >= 5:
            second_oldest_drops += 1
        if step >= 6:
            second_oldest_drops += 1
        if second_oldest_drops > 0 and len(exps) >= 2:
            target = len(exps) - 1  # last entry = second-oldest (oldest may have been dropped)
            remaining = exps[target].bullets[:-second_oldest_drops]
            if remaining:
                exps[target] = TailoredExperience(role_id=exps[target].role_id, bullets=remaining)
            else:
                exps = exps[:target]  # drop the role if emptied

        # Step 7: trim newest role by 1 (protect at least 1 bullet)
        if step >= 7 and exps and len(exps[0].bullets) > 1:
            exps[0] = TailoredExperience(role_id=exps[0].role_id, bullets=exps[0].bullets[:-1])

        return TailoredContent(
            summary=tailored.summary,
            skills=tailored.skills,
            experience=exps,
            projects=projs,
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _ensure_https(url: str) -> str:
        if url and not url.startswith(("http://", "https://")):
            return "https://" + url
        return url

    @staticmethod
    def _display_url(url: str) -> str:
        return url.replace("https://", "").replace("http://", "")

    # ── Section builders ───────────────────────────────────────────────────────

    @staticmethod
    def _section_heading(title: str) -> str:
        """A 12pt, uppercase, ruled section heading (matches the template)."""
        return (
            f"\\section*{{\\fontsize{{12}}{{14}} \\selectfont {title}}}\\vspace{{-0.4cm}}\n"
            "\\hrule\\vspace{0.1cm}"
        )

    def _preamble(self) -> str:
        return r"""\documentclass[a4paper,10pt]{article}
\usepackage[utf8]{inputenc}
\usepackage{geometry}
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    urlcolor=black,
    pdfborder={0 0 0}
}
\usepackage{enumitem}
\usepackage{titlesec}
\usepackage{setspace}
\usepackage{amssymb}
\usepackage{xcolor}
\definecolor{lightblue}{RGB}{0, 0, 205}
\usepackage{graphicx}
\geometry{left=0.5in, right=0.5in, top=0.5in, bottom=0.5in}
\renewcommand{\baselinestretch}{1.1}
\begin{document}
\pagestyle{empty}"""

    def _personal_section(self, profile: Profile) -> str:
        p = profile.personal
        contacts: list[str] = []
        if p.email:
            contacts.append(f"\\href{{mailto:{escape(p.email)}}}{{{escape(p.email)}}}")
        if p.phone:
            contacts.append(escape(p.phone))
        if p.location:
            contacts.append(escape(p.location))
        if p.linkedin:
            url = self._ensure_https(p.linkedin)
            contacts.append(f"\\href{{{escape(url)}}}{{{escape(self._display_url(p.linkedin))}}}")
        if p.portfolio:
            url = self._ensure_https(p.portfolio)
            contacts.append(f"\\href{{{escape(url)}}}{{Portfolio}}")
        if p.github:
            url = self._ensure_https(p.github)
            display = escape(p.github_display or self._display_url(p.github))
            contacts.append(f"\\href{{{escape(url)}}}{{{display}}}")

        contact_line = " \\textbar{} ".join(contacts)
        return (
            "\\begin{center}\n"
            f"    {{\\LARGE \\textbf{{{escape(p.name)}}}}} \\\\\n"
            "    \\vspace{0.1cm}\n"
            f"    {contact_line}\n"
            "\\end{center}\n"
            "\\vspace{-0.2cm}\n"
            "\\hrule\n"
            "\\vspace{0.2cm}"
        )

    def _summary_section(self, tailored: TailoredContent) -> str:
        # Rendered as the template's "Objective" line: italic, no section heading.
        if not tailored.summary or not tailored.summary.strip():
            return ""
        return (
            "\\noindent\n"
            f"\\textit{{{escape(tailored.summary)}}}\n"
            "\\vspace{-0.4cm}"
        )

    def _education_section(self, profile: Profile) -> str:
        if not profile.education:
            return ""
        lines = ["\\begin{spacing}{1.0}", self._section_heading("EDUCATION")]
        for i, edu in enumerate(profile.education):
            school_line = f"\\textbf{{{escape(edu.school)}}}"
            if edu.location:
                school_line += f", {escape(edu.location)}"
            if edu.dates:
                school_line += f" \\hfill \\textit{{{escape(edu.dates)}}}"
            lines.append(school_line + " \\\\")

            degree_line = escape(edu.degree)
            if edu.gpa:
                degree_line += f" \\hfill GPA: {edu.gpa:.2f}"
            lines.append(degree_line + " \\\\")

            if edu.coursework:
                cw = ", ".join(escape(c) for c in edu.coursework)
                lines.append(f"Relevant Coursework: {cw} \\\\")

            # Gap between education entries (template uses \\[0.2cm]).
            if i < len(profile.education) - 1:
                lines.append("\\vspace{0.2cm}")
        lines.append("\\end{spacing}")
        lines.append("\\vspace{-1cm}")
        return "\n".join(lines)

    def _skills_section(self, tailored: TailoredContent) -> str:
        if not tailored.skills:
            return ""
        lines = [self._section_heading("SKILLS")]
        for category, skill_list in tailored.skills.items():
            skills_str = ", ".join(escape(s) for s in skill_list)
            lines.append(f"\\textbf{{{escape(category)}:}} {skills_str} \\\\")
        lines.append("\\vspace{-0.4cm}")
        return "\n".join(lines)

    def _experience_section(self, profile: Profile, tailored: TailoredContent) -> str:
        if not tailored.experience:
            return ""

        # Build lookup: role_id → Experience metadata
        exp_meta = {exp.id: exp for exp in profile.experience}

        lines = [self._section_heading("EXPERIENCE")]
        for idx, te in enumerate(tailored.experience):
            meta = exp_meta.get(te.role_id)
            if meta is None:
                logger.warning(f"TailoredExperience role_id={te.role_id!r} not found in profile; skipping")
                continue

            if idx > 0:
                lines.append("\\vspace{0.1cm}")

            company_line = f"\\noindent\n\\textbf{{\\textcolor{{lightblue}}{{{escape(meta.company)}}}}}"
            if meta.location:
                company_line += f" \\hfill \\textit{{{escape(meta.location)}}}"
            lines.append(company_line + " \\\\")

            title_line = f"\\textbf{{{escape(meta.title)}}}"
            if meta.dates:
                title_line += f" \\hfill \\textit{{{escape(meta.dates)}}}"
            lines.append(title_line)

            if te.bullets:
                lines.append(
                    "\\begin{itemize}[noitemsep, topsep=0pt, leftmargin=0.7cm, label=\\scriptsize$\\bullet$]"
                )
                for bullet in te.bullets:
                    lines.append(f"    \\item {escape(bullet)}")
                lines.append("\\end{itemize}")

        return "\n".join(lines)

    def _projects_section(self, profile: Profile, tailored: TailoredContent) -> str:
        if not tailored.projects:
            return ""

        # Build lookup: project_id → Project metadata
        proj_meta = {p.id: p for p in profile.projects}

        lines = [self._section_heading("PROJECTS")]
        for tp in tailored.projects:
            meta = proj_meta.get(tp.project_id)
            if meta is None:
                logger.warning(f"TailoredProject project_id={tp.project_id!r} not found in profile; skipping")
                continue

            # Header: name [- GitHub] [\hfill stack]
            header = f"\\noindent\n\\textbf{{{escape(meta.name)}}}"
            if meta.subtitle:
                header += f" --- {escape(meta.subtitle)}"
            if meta.url:
                url = self._ensure_https(meta.url)
                header += f"- \\href{{{escape(url)}}}{{\\textit{{GitHub}}}}"
            right = meta.stack or meta.themes
            if right:
                stack_str = ", ".join(escape(s) for s in right)
                header += f" \\hfill \\textit{{{stack_str}}}"
            lines.append(header)

            if meta.text:
                lines.append(
                    "\\begin{itemize}[noitemsep, topsep=0pt, partopsep=0pt, parsep=0pt, "
                    "leftmargin=0.7cm, label=\\scriptsize$\\bullet$]"
                )
                lines.append(f"    \\item {escape(meta.text)}")
                lines.append("\\end{itemize}\\vspace{-0.1cm}")

        return "\n".join(lines)
